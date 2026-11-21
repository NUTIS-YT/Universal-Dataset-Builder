"""Dataset browser with thumbnails, caption editing and source scanning."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QIcon, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from universal_dataset_builder.core.project import Project
from universal_dataset_builder.dataset.metadata import sync_training_metadata
from universal_dataset_builder.storage.database import (
    IMAGE_STATUSES,
    read_images,
    save_image_caption,
    set_image_status,
)
from universal_dataset_builder.workers.scan_worker import ScanWorker


def _read_scaled_pixmap(path: Path, bounds: QSize) -> QPixmap:
    """Load an image at a bounded size, applying its EXIF display orientation."""
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    source_size = reader.size()
    if source_size.isValid():
        reader.setScaledSize(source_size.scaled(bounds, Qt.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        return QPixmap()
    return QPixmap.fromImage(image).scaled(
        bounds,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )


class ImageViewerDialog(QDialog):
    """Display a selected image scaled to fit a resizable window."""

    def __init__(self, image_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image_path = Path(image_path)
        self.setWindowTitle(self.image_path.name)
        self.resize(960, 720)
        self.setMinimumSize(480, 360)

        layout = QVBoxLayout(self)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setObjectName("ImagePreview")
        layout.addWidget(self.image_label, 1)
        self._render_image()

    def _render_image(self) -> None:
        bounds = QSize(max(self.width() - 40, 320), max(self.height() - 80, 240))
        pixmap = _read_scaled_pixmap(self.image_path, bounds)
        if pixmap.isNull():
            self.image_label.setText("Unable to open this image.")
        else:
            self.image_label.setPixmap(pixmap)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_image()


class DatasetPage(QWidget):
    """Run source scans and review indexed images with their captions."""

    scan_completed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.project: Project | None = None
        self._worker: ScanWorker | None = None
        self._images: dict[int, dict[str, object]] = {}
        self._selected_image_id: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search image filename…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._refresh_gallery)
        toolbar.addWidget(self.search_edit, 1)

        self.status_filter = QComboBox()
        self.status_filter.addItem("All statuses", "")
        for status in IMAGE_STATUSES:
            self.status_filter.addItem(status, status)
        self.status_filter.currentIndexChanged.connect(self._refresh_gallery)
        toolbar.addWidget(self.status_filter)

        self.scan_button = QPushButton("Scan source")
        self.scan_button.setObjectName("PrimaryButton")
        self.scan_button.setEnabled(False)
        self.scan_button.clicked.connect(self.start_scan)
        toolbar.addWidget(self.scan_button)
        layout.addLayout(toolbar)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Create or open a project to browse its images.")
        self.status_label.setObjectName("MutedText")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        splitter = QSplitter(Qt.Horizontal)
        self.gallery = QListWidget()
        self.gallery.setObjectName("DatasetGallery")
        self.gallery.setViewMode(QListView.IconMode)
        self.gallery.setFlow(QListView.LeftToRight)
        self.gallery.setWrapping(True)
        self.gallery.setResizeMode(QListView.Adjust)
        self.gallery.setMovement(QListView.Static)
        self.gallery.setSelectionMode(QAbstractItemView.SingleSelection)
        self.gallery.setIconSize(QSize(112, 112))
        self.gallery.setGridSize(QSize(148, 158))
        self.gallery.setSpacing(8)
        self.gallery.itemSelectionChanged.connect(self._selection_changed)
        splitter.addWidget(self.gallery)

        details = QWidget()
        details.setObjectName("DatasetDetails")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(12, 8, 4, 4)
        details_layout.setSpacing(8)

        self.image_title = QLabel("Select an image")
        self.image_title.setObjectName("SectionTitle")
        self.image_title.setWordWrap(True)
        details_layout.addWidget(self.image_title)

        self.image_info = QLabel("")
        self.image_info.setObjectName("MutedText")
        self.image_info.setWordWrap(True)
        details_layout.addWidget(self.image_info)

        self.image_preview = QLabel("Image preview")
        self.image_preview.setObjectName("ImagePreview")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumHeight(190)
        details_layout.addWidget(self.image_preview, 1)

        preview_actions = QHBoxLayout()
        self.open_image_button = QPushButton("View full image")
        self.open_image_button.setEnabled(False)
        self.open_image_button.clicked.connect(self.open_full_image)
        preview_actions.addWidget(self.open_image_button)
        preview_actions.addStretch(1)
        details_layout.addLayout(preview_actions)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Image status"))
        self.status_editor = QComboBox()
        for status in IMAGE_STATUSES:
            self.status_editor.addItem(status, status)
        status_row.addWidget(self.status_editor, 1)
        self.apply_status_button = QPushButton("Apply")
        self.apply_status_button.setEnabled(False)
        self.apply_status_button.clicked.connect(self.apply_selected_status)
        status_row.addWidget(self.apply_status_button)
        details_layout.addLayout(status_row)

        caption_title = QLabel("Training caption")
        caption_title.setObjectName("SectionTitle")
        details_layout.addWidget(caption_title)

        self.caption_editor = QTextEdit()
        self.caption_editor.setPlaceholderText(
            "Write or correct an English caption for this image…"
        )
        self.caption_editor.setMinimumHeight(105)
        self.caption_editor.setEnabled(False)
        details_layout.addWidget(self.caption_editor)

        self.save_caption_button = QPushButton("Save caption")
        self.save_caption_button.setObjectName("PrimaryButton")
        self.save_caption_button.setEnabled(False)
        self.save_caption_button.clicked.connect(self.save_caption)
        details_layout.addWidget(self.save_caption_button)

        splitter.addWidget(details)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 5)
        layout.addWidget(splitter, 1)

    def set_project(self, project: Project | None) -> None:
        """Attach the active project and refresh the browser."""
        self.project = project
        self.scan_button.setEnabled(project is not None and self._worker is None)
        if project is None:
            self._images.clear()
            self._selected_image_id = None
            self.gallery.clear()
            self._clear_details()
            self.status_label.setText("Create or open a project to browse its images.")
            return
        self._refresh_gallery()

    def refresh(self) -> None:
        """Reload image records and thumbnails after an external dataset operation."""
        self._refresh_gallery()

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
        self._refresh_gallery()

        discovered = getattr(summary, "discovered", 0)
        added = getattr(summary, "added", 0)
        updated = getattr(summary, "updated", 0)
        unchanged = getattr(summary, "unchanged", 0)
        failed = getattr(summary, "failed", 0)
        message = (
            f"Scan complete: {discovered} found · {added} added · "
            f"{updated} updated · {unchanged} unchanged · {failed} unreadable."
        )
        metadata_warning = getattr(summary, "metadata_warning", None)
        if metadata_warning:
            message += f" metadata.jsonl update failed: {metadata_warning}"
            self.status_label.setToolTip(str(metadata_warning))
        else:
            self.status_label.setToolTip("")
        self.status_label.setText(message)
        self.scan_completed.emit()

    def _scan_failed(self, message: str) -> None:
        self._worker = None
        self.progress.setVisible(False)
        self.scan_button.setEnabled(self.project is not None)
        self.status_label.setText(f"Scan failed: {message}")

    def _refresh_gallery(self, *_args) -> None:
        if self.project is None:
            self.gallery.clear()
            self._images.clear()
            self._clear_details()
            return

        selected_id = self._selected_image_id
        try:
            rows = read_images(self.project.path)
        except (OSError, ValueError) as error:
            self.status_label.setText(f"Could not load indexed images: {error}")
            return

        self._images = {int(row["image_id"]): row for row in rows}
        query = self.search_edit.text().strip().casefold()
        selected_status = str(self.status_filter.currentData() or "")
        filtered = [
            row
            for row in rows
            if (not query or query in str(row["filename"]).casefold())
            and (not selected_status or row["status"] == selected_status)
        ]

        self.gallery.blockSignals(True)
        self.gallery.clear()
        selected_item = None
        for row in filtered:
            image_id = int(row["image_id"])
            filename = str(row["filename"])
            status = str(row["status"])
            image_path = self._image_path(row)

            item = QListWidgetItem()
            item.setText(f"{Path(filename).name}\n{status}")
            item.setData(Qt.UserRole, image_id)
            item.setToolTip(
                f"{filename}\n{row['width'] or '—'} × {row['height'] or '—'}"
                f" · {row['format'] or 'Unknown'}\n{image_path}"
            )
            if image_path.is_file():
                pixmap = _read_scaled_pixmap(image_path, QSize(112, 112))
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap))
            self.gallery.addItem(item)
            if image_id == selected_id:
                selected_item = item

        self.gallery.blockSignals(False)
        if selected_item is not None:
            self.gallery.setCurrentItem(selected_item)
        elif self.gallery.count():
            self.gallery.setCurrentRow(0)
        else:
            self._selected_image_id = None
            self._clear_details()

        if not rows:
            self.status_label.setText(
                "No images indexed yet. Put images in source/ and select Scan source."
            )
        elif not filtered:
            self.status_label.setText("No images match the current search and status filter.")
        else:
            self.status_label.setText(f"Showing {len(filtered)} of {len(rows)} indexed images.")

    @staticmethod
    def _image_path(image: dict[str, object]) -> Path:
        normalized = image.get("normalized_path")
        if normalized:
            candidate = Path(str(normalized))
            if candidate.is_file():
                return candidate
        return Path(str(image["original_path"]))

    def _selection_changed(self) -> None:
        item = self.gallery.currentItem()
        if item is None:
            self._selected_image_id = None
            self._clear_details()
            return

        image_id = int(item.data(Qt.UserRole))
        self._selected_image_id = image_id
        image = self._images.get(image_id)
        if image is None:
            self._clear_details()
            return

        filename = str(image["filename"])
        width = image["width"]
        height = image["height"]
        self.image_title.setText(filename)
        self.image_info.setText(
            f"{width or '—'} × {height or '—'} · {image['format'] or 'Unknown'}"
            f" · {image['status']}"
        )
        self.caption_editor.setPlainText(str(image.get("caption_text") or ""))
        status_index = self.status_editor.findData(str(image["status"]))
        self.status_editor.setCurrentIndex(max(status_index, 0))
        self.caption_editor.setEnabled(True)
        self.save_caption_button.setEnabled(True)
        self.apply_status_button.setEnabled(True)
        self.open_image_button.setEnabled(self._image_path(image).is_file())
        self._refresh_selected_preview()

    def _clear_details(self) -> None:
        self.image_title.setText("Select an image")
        self.image_info.clear()
        self.image_preview.setPixmap(QPixmap())
        self.image_preview.setText("Image preview")
        self.caption_editor.clear()
        self.caption_editor.setEnabled(False)
        self.save_caption_button.setEnabled(False)
        self.apply_status_button.setEnabled(False)
        self.open_image_button.setEnabled(False)

    def _refresh_selected_preview(self) -> None:
        image = self._images.get(self._selected_image_id or -1)
        if image is None:
            return
        image_path = self._image_path(image)
        if not image_path.is_file():
            self.image_preview.setPixmap(QPixmap())
            self.image_preview.setText("Source image is missing.")
            self.open_image_button.setEnabled(False)
            return

        bounds = QSize(
            max(self.image_preview.width() - 20, 300),
            max(self.image_preview.height() - 20, 160),
        )
        pixmap = _read_scaled_pixmap(image_path, bounds)
        if pixmap.isNull():
            self.image_preview.setPixmap(QPixmap())
            self.image_preview.setText("Unable to decode image preview.")
        else:
            self.image_preview.setText("")
            self.image_preview.setPixmap(pixmap)

    def open_full_image(self) -> None:
        """Open the selected source or normalized image in a larger viewer."""
        image = self._images.get(self._selected_image_id or -1)
        if image is None:
            return
        image_path = self._image_path(image)
        if not image_path.is_file():
            self.status_label.setText("The selected image file no longer exists.")
            return
        dialog = ImageViewerDialog(image_path, self)
        dialog.exec()

    def save_caption(self) -> None:
        """Save the edited caption and synchronize the project JSONL manifest."""
        if self.project is None or self._selected_image_id is None:
            self.status_label.setText("Select an image before saving a caption.")
            return

        caption = self.caption_editor.toPlainText()
        try:
            save_image_caption(
                self.project.path,
                self._selected_image_id,
                caption,
            )
        except (OSError, ValueError) as error:
            self.status_label.setText(f"Could not save caption: {error}")
            return

        try:
            sync_training_metadata(self.project.path, self.project.dataset_path)
        except Exception as error:
            self.status_label.setText(
                f"Caption saved, but metadata.jsonl could not be updated: {error}"
            )
        else:
            self.status_label.setText(
                "Caption saved and marked as Reviewed. metadata.jsonl updated."
            )

        self._refresh_gallery()

    def apply_selected_status(self) -> None:
        """Apply the selected status after validating the caption prerequisites."""
        if self.project is None or self._selected_image_id is None:
            return
        status = str(self.status_editor.currentData())
        try:
            set_image_status(self.project.path, self._selected_image_id, status)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot change image status", str(error))
            return

        try:
            sync_training_metadata(self.project.path, self.project.dataset_path)
        except Exception as error:
            QMessageBox.warning(
                self,
                "Metadata update failed",
                f"Image status changed, but metadata.jsonl could not be updated: {error}",
            )

        self._refresh_gallery()
        self.status_label.setText(f"Image status changed to {status}.")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_selected_preview()
