"""Qt application construction and global metadata."""

from __future__ import annotations

import logging
import sys
from types import TracebackType

from PySide6.QtWidgets import QApplication

from universal_dataset_builder import __version__

LOGGER = logging.getLogger(__name__)


def create_application() -> QApplication:
    """Create or return the QApplication instance."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])

    application.setApplicationName("Universal Dataset Builder")
    application.setApplicationDisplayName("Universal Dataset Builder")
    application.setOrganizationName("NUTIS-YT")
    application.setApplicationVersion(__version__)

    def handle_exception(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        LOGGER.critical(
            "Uncaught application exception",
            exc_info=(exception_type, exception, traceback),
        )

    sys.excepthook = handle_exception
    return application
