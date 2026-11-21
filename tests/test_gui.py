from __future__ import annotations

import os

from PySide6.QtWidgets import QApplication

from universal_dataset_builder.gui.main_window import MainWindow


def test_main_window_builds_navigation_and_switches_theme(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    application = QApplication.instance()
    if application is None:
        application = QApplication([])

    window = MainWindow()
    assert window.pages.count() == 6
    assert len(window.navigation_buttons) == 6
    assert window.windowTitle() == "Universal Dataset Builder"

    window.show_page(3)
    assert window.pages.currentIndex() == 3
    assert window.page_title.text() == "Caption Generator"

    window.settings_page.theme_selector.setCurrentIndex(1)
    assert window.config.get("theme") == "light"

    window.close()
    application.processEvents()
