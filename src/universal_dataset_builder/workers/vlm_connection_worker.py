"""Worker for testing a VLM endpoint and retrieving its models."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from universal_dataset_builder.vlm.client import OpenAICompatibleClient

LOGGER = logging.getLogger(__name__)


class VLMConnectionSignals(QObject):
    """Signals emitted by the connection test."""

    completed = Signal(str, object)
    failed = Signal(str)


class VLMConnectionWorker(QRunnable):
    """Fetch the model list outside the GUI thread."""

    def __init__(self, base_url: str, api_key: str, timeout_seconds: int) -> None:
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.signals = VLMConnectionSignals()

    @Slot()
    def run(self) -> None:
        try:
            with OpenAICompatibleClient(
                self.base_url,
                api_key=self.api_key,
                timeout_seconds=self.timeout_seconds,
            ) as client:
                models = client.list_models()
                normalized_url = client.base_url
        except Exception as error:
            LOGGER.exception("VLM connection test failed")
            self.signals.failed.emit(str(error))
        else:
            self.signals.completed.emit(normalized_url, models)
