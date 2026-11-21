from __future__ import annotations

from PySide6.QtWidgets import QApplication

from universal_dataset_builder.gui.main_window import MainWindow
from universal_dataset_builder.gui.styles.theme_manager import ThemeManager


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
    assert window.centralWidget().objectName() == "CentralWidget"
    assert window.pages.widget(1) is window.dataset_page

    window.show_page(1)
    assert window.page_title.text() == "Dataset"

    window.show_page(3)
    assert window.pages.currentIndex() == 3
    assert window.page_title.text() == "Caption Generator"

    window.settings_page.theme_selector.setCurrentIndex(1)
    assert window.config.get("theme") == "light"

    window.close()
    application.processEvents()


def test_theme_does_not_paint_every_child_widget():
    dark = ThemeManager.stylesheet("dark")
    light = ThemeManager.stylesheet("light")

    assert "QWidget {\n        color:" in dark
    assert "QWidget {\n        background-color:" not in dark
    assert "QWidget {\n        background-color:" not in light
    assert "#CentralWidget { background-color:" in dark
    assert "#CentralWidget { background-color:" in light
