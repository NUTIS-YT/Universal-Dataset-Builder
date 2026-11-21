"""Image normalization settings and background progress UI."""

from __future__ import annotations

from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from universal_dataset_builder.core.project import Project
from universal_dataset_builder.dataset.normalizer import NormalizationSummary
from universal_dataset_builder.workers.normalizer_worker import NormalizerWorker


class NormalizerPage(QWidget):
    """Configure and run safe image normalization for the active project."""

    normalization_completed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.project: Project | None = None
        self._worker: NormalizerWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("Image Normalizer")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        description = QLabel(
            "Convert indexed source images into consistently named PNG files inside "
            "dataset/. Original images in source/ are never modified."
        )
        description.setObjectName("MutedText")
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.start_number = QSpinBox()
        self.start_number.setRange(1, 999_999_999)
        self.start_number.setValue(1)
        self.start_number.setSuffix("  (00001.png)")
        form.addRow("Starting number", self.start_number)

        self.sort_selector = QComboBox()
        self.sort_selector.addItem("Filename (A–Z)", "filename_asc")
        self.sort_selector.addItem("Filename (Z–A)", "filename_desc")
        self.sort_selector.addItem("Largest image first", "largest_first")
        self.sort_selector.addItem("Smallest image first", "smallest_first")
        form.addRow("Image order", self.sort_selector)

        self.alpha_selector = QComboBox()
        self.alpha_selector.addItem("Preserve transparency", "preserve")
        self.alpha_selector.addItem("Flatten onto white", "white")
        self.alpha_selector.addItem("Flatten onto black", "black")
        form.addRow("Transparency", self.alpha_selector)

        self.skip_duplicates = QCheckBox("Skip exact visual duplicates")
        self.skip_duplicates.setChecked(True)
        form.addRow("Duplicates", self.skip_duplicates)
        layout.addLayout(form)

        self.output_label = QLabel("Output: no project open")
        self.output_label.setObjectName("MutedText")
        self.output_label.setWordWrap(True)
        layout.addWidget(self.output_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel(
            "Create or open a project to configure image normalization."
        )
        self.status_label.setObjectName("MutedText")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        actions = QHBoxLayout()
        self.start_button = QPushButton("Normalize images")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_normalization)
        actions.addWidget(self.start_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)

    def set_project(self, project: Project | None) -> None:
        """Attach the active project."""
        self.project = project
        if project is None:
            self.output_label.setText("Output: no project open")
            self.status_label.setText(
                "Create or open a project to configure image normalization."
            )
        else:
            self.output_label.setText(f"Output directory: {project.dataset_path}")
            self.status_label.setText("Ready to normalize indexed source images.")
        self._update_controls()

    def _update_controls(self) -> None:
        busy = self._worker is not None
        self.start_button.setEnabled(self.project is not None)
        self.start_button.setText("Cancel normalization" if busy else "Normalize images")
        if busy:
            self.start_button.clicked.disconnect()
            self.start_button.clicked.connect(self.cancel_normalization)
        else:
            try:
                self.start_button.clicked.disconnect()
            except RuntimeError:
                pass
            self.start_button.clicked.connect(self.start_normalization)

    def start_normalization(self) -> None:
        """Start a normalization task on the Qt thread pool."""
        if self.project is None or self._worker is not None:
            return

        project = self.project
        worker = NormalizerWorker(
            project.path,
            project.source_path,
            project.dataset_path,
            start_number=self.start_number.value(),
            alpha_mode=str(self.alpha_selector.currentData()),
            skip_duplicates=self.skip_duplicates.isChecked(),
            sort_mode=str(self.sort_selector.currentData()),
        )
        worker.signals.progress.connect(self._update_progress)
        worker.signals.completed.connect(self._normalization_finished)
        worker.signals.failed.connect(self._normalization_failed)
        self._worker = worker
        self.progress.setRange(0, 0)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.status_label.setText("Preparing image normalization…")
        self._update_controls()
        QThreadPool.globalInstance().start(worker)

    def cancel_normalization(self) -> None:
        """Ask the worker to stop after the current image."""
        if self._worker is not None:
            self._worker.cancel()
            self.start_button.setEnabled(False)
            self.status_label.setText("Cancellation requested. Finishing current image…")

    def _update_progress(self, current: int, total: int, filename: str) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(current)
        self.status_label.setText(f"Processing {filename} · {current}/{total}")

    def _normalization_finished(self, summary: object) -> None:
        self._worker = None
        self.progress.setVisible(False)
        self._update_controls()

        result = summary
        if not isinstance(result, NormalizationSummary):
            self.status_label.setText("Normalization completed with an invalid result.")
            return

        state = "Cancelled" if result.cancelled else "Complete"
        self.status_label.setText(
            f"{state}: {result.normalized} normalized · "
            f"{result.already_normalized} already present · "
            f"{result.duplicates} duplicates skipped · "
            f"{result.conflicts} filename conflicts avoided · "
            f"{result.failed} failed."
        )
        if result.failed_files:
            details = "\n".join(result.failed_files[:12])
            if len(result.failed_files) > 12:
                details += f"\n…and {len(result.failed_files) - 12} more."
            self.status_label.setToolTip(details)
        else:
            self.status_label.setToolTip("")
        self.normalization_completed.emit()

    def _normalization_failed(self, message: str) -> None:
        self._worker = None
        self.progress.setVisible(False)
        self._update_controls()
        self.status_label.setText(f"Normalization failed: {message}")
