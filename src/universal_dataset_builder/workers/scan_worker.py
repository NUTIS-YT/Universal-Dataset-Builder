"""Qt background worker adapting dataset scanning to Qt signals."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from universal_dataset_builder.dataset.scanner import ScanSummary
from universal_dataset_builder.services.dataset_service import DatasetService

LOGGER = logging.getLogger(__name__)


class ScanWorkerSignals(QObject):
    """Signals emitted by a background scan."""

    progress = Signal(int, int)
    completed = Signal(object)
    failed = Signal(str)


class ScanWorker(QRunnable):
    """Run the shared scan service on the global Qt thread pool."""

    def __init__(self, database_path: Path, source_path: Path) -> None:
        super().__init__()
        self.database_path = Path(database_path)
        self.source_path = Path(source_path)
        self.signals = ScanWorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            summary: ScanSummary = DatasetService.scan_source(
                self.database_path,
                self.source_path,
                progress_callback=self.signals.progress.emit,
            )
        except Exception as error:
            LOGGER.exception("Dataset scan failed")
            self.signals.failed.emit(str(error))
        else:
            self.signals.completed.emit(summary)
