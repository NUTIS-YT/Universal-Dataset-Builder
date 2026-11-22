"""Qt background worker adapting image normalization to Qt signals."""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from universal_dataset_builder.dataset.normalizer import NormalizationSummary
from universal_dataset_builder.services.dataset_service import DatasetService

LOGGER = logging.getLogger(__name__)


class NormalizerWorkerSignals(QObject):
    """Signals emitted by a normalization worker."""

    progress = Signal(int, int, str)
    completed = Signal(object)
    failed = Signal(str)


class NormalizerWorker(QRunnable):
    """Execute the shared normalization service outside the GUI thread."""

    def __init__(
        self,
        database_path: Path,
        source_path: Path,
        dataset_path: Path,
        *,
        start_number: int,
        alpha_mode: str,
        skip_duplicates: bool,
        sort_mode: str,
    ) -> None:
        super().__init__()
        self.database_path = Path(database_path)
        self.source_path = Path(source_path)
        self.dataset_path = Path(dataset_path)
        self.start_number = start_number
        self.alpha_mode = alpha_mode
        self.skip_duplicates = skip_duplicates
        self.sort_mode = sort_mode
        self._cancel_event = Event()
        self.signals = NormalizerWorkerSignals()

    def cancel(self) -> None:
        """Request cancellation between images."""
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            summary: NormalizationSummary = DatasetService.normalize_images(
                self.database_path,
                self.source_path,
                self.dataset_path,
                start_number=self.start_number,
                alpha_mode=self.alpha_mode,
                skip_duplicates=self.skip_duplicates,
                sort_mode=self.sort_mode,
                progress_callback=self.signals.progress.emit,
                cancel_requested=self._cancel_event.is_set,
            )
        except Exception as error:
            LOGGER.exception("Image normalization failed")
            self.signals.failed.emit(str(error))
        else:
            self.signals.completed.emit(summary)
