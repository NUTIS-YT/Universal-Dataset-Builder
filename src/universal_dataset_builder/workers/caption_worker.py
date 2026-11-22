"""Qt background worker adapting the shared caption service to Qt signals."""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from universal_dataset_builder.services.caption_service import (
    CaptionGenerationService,
    CaptionSummary,
    select_caption_targets,
)

LOGGER = logging.getLogger(__name__)


class CaptionWorkerSignals(QObject):
    """Signals emitted by a batch caption task."""

    progress = Signal(int, int, str)
    completed = Signal(object)
    failed = Signal(str)


class CaptionWorker(QRunnable):
    """Adapt the shared caption service to the existing Qt thread pool."""

    def __init__(
        self,
        database_path: Path,
        source_directory: Path,
        dataset_directory: Path,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
        model: str,
        prompt: str,
        selection_mode: str,
        limit: int,
    ) -> None:
        super().__init__()
        self.database_path = Path(database_path)
        self.source_directory = Path(source_directory)
        self.dataset_directory = Path(dataset_directory)
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.prompt = prompt
        self.selection_mode = selection_mode
        self.limit = limit
        self._cancel_event = Event()
        self.signals = CaptionWorkerSignals()

    def cancel(self) -> None:
        """Request cancellation between image requests."""
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            summary: CaptionSummary = CaptionGenerationService.generate(
                self.database_path,
                self.source_directory,
                self.dataset_directory,
                base_url=self.base_url,
                api_key=self.api_key,
                timeout_seconds=self.timeout_seconds,
                model=self.model,
                prompt=self.prompt,
                selection_mode=self.selection_mode,
                limit=self.limit,
                cancel_requested=self._cancel_event.is_set,
                progress_callback=self.signals.progress.emit,
            )
        except Exception as error:
            LOGGER.exception("Caption generation task failed")
            self.signals.failed.emit(str(error))
        else:
            self.signals.completed.emit(summary)
