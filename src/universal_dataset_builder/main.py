"""Application entry point and interface launcher."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QMessageBox

from .core.application import create_application
from .core.config import ConfigStore
from .gui.launcher import (
    LauncherDialog,
    launch_expressive_ui,
    start_api_server,
    stop_api_server,
)
from .gui.main_window import MainWindow
from .gui.styles.theme_manager import ThemeManager


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def legacy_main() -> int:
    """Start the established PySide6 interface directly."""
    _configure_logging()
    application = create_application()
    window = MainWindow()
    window.show()
    return application.exec()


def main() -> int:
    """Show the UI selector and start the required services automatically."""
    _configure_logging()
    application = create_application()
    config = ConfigStore()
    application.setStyleSheet(ThemeManager.stylesheet(config.get("theme", "dark")))
    application.setQuitOnLastWindowClosed(False)

    dialog = LauncherDialog()
    if dialog.exec() != dialog.DialogCode.Accepted:
        return 0

    if dialog.selected_mode == "legacy":
        application.setQuitOnLastWindowClosed(True)
        window = MainWindow()
        window.show()
        return application.exec()

    api_process, error = start_api_server()
    if error is not None:
        QMessageBox.critical(None, "Local API could not start", error)
        return 1

    try:
        return launch_expressive_ui()
    finally:
        stop_api_server(api_process)


if __name__ == "__main__":
    raise SystemExit(main())
