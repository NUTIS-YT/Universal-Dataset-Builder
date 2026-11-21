"""Application entry point."""

from __future__ import annotations

import logging

from .core.application import create_application
from .gui.main_window import MainWindow


def main() -> int:
    """Start the desktop application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    application = create_application()
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
