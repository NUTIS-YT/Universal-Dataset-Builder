"""Dataset scanner and indexed-image browser."""

from __future__ import annotations

from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from universal_dataset_builder.core.project import Project
from universal_dataset_builder.storage.database import read_images
from universal_dataset_builder.workers.scan_worker import ScanWorker


class DatasetPage(QWidget):
    """Run source scans in the background and display indexed image metadata."""

    scan_completed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.project: Project | None = None
        self._worker: ScanWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Dataset Scanner")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        description = QLabel(
            "Scan the project's source/ folder. Original images are read in place "
            "and are never moved or modified."
        )
        description.setObjectName("MutedText")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.scan_button = QPushButton("Scan source folder")
        self.scan_button.setObjectName("PrimaryButton")
        self.scan_button.setEnabled(False)
        self.scan_button.clicked.connect(self.start_scan)
        layout.addWidget(self.scan_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Create or open a project to scan its source/ folder.")
        self.status_label.setObjectName("MutedText")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(("Source file", "Dimensions", "Format", "Status"))
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 4):
            self.table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeToContents
            )
        layout.addWidget(self.table, 1)

    def set_project(self, project: Project | None) -> None:
        """Attach the active project and refresh the image list."""
        self.project = project
        self.scan_button.setEnabled(project is not None and self._worker is None)
        if project is None:
            self.table.setRowCount(0)
            self.status_label.setText("Create or open a project to scan its source/ folder.")
            return
        self._refresh_table()

    def start_scan(self) -> None:
        """Start scanning without blocking the Qt event loop."""
        if self.project is None or self._worker is not None:
            return

        self.scan_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.status_label.setText("Preparing source folder scan…")

        worker = ScanWorker(self.project.path, self.project.source_path)
        worker.signals.progress.connect(self._update_progress)
        worker.signals.completed.connect(self._scan_finished)
        worker.signals.failed.connect(self._scan_failed)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    def _update_progress(self, current: int, total: int) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(current)
        self.status_label.setText(f"Scanning images… {current} / {total}")

    def _scan_finished(self, summary: object) -> None:
        self._worker = None
        self.progress.setVisible(False)
        self.scan_button.setEnabled(self.project is not None)
        self._refresh_table()

        discovered = getattr(summary, "discovered", 0)
        added = getattr(summary, "added", 0)
        updated = getattr(summary, "updated", 0)
        unchanged = getattr(summary, "unchanged", 0)
        failed = getattr(summary, "failed", 0)
        self.status_label.setText(
            f"Scan complete: {discovered} found · {added} added · "
            f"{updated} updated · {unchanged} unchanged · {failed} unreadable."
        )
        self.scan_completed.emit()

    def _scan_failed(self, message: str) -> None:
        self._worker = None
        self.progress.setVisible(False)
        self.scan_button.setEnabled(self.project is not None)
        self.status_label.setText(f"Scan failed: {message}")

    def _refresh_table(self) -> None:
        if self.project is None:
            self.table.setRowCount(0)
            return

        try:
            images = read_images(self.project.path)
        except (OSError, ValueError) as error:
            self.status_label.setText(f"Could not load indexed images: {error}")
            self.table.setRowCount(0)
            return

        self.table.setRowCount(len(images))
        for row, image in enumerate(images):
            width = image["width"]
            height = image["height"]
            dimensions = f"{width} × {height}" if width and height else "—"
            values = (
                str(image["filename"]),
                dimensions,
                str(image["format"] or "—"),
                str(image["status"]),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

        if not images:
            self.status_label.setText(
                "No images indexed yet. Put images in the project's source/ folder "
                "and select Scan source folder."
            )
        else:
            self.status_label.setText(f"{len(images)} image file(s) indexed.")
