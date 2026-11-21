from __future__ import annotations

from PIL import Image
from PySide6.QtWidgets import QApplication

from universal_dataset_builder.core.project import Project
from universal_dataset_builder.dataset.scanner import scan_directory
from universal_dataset_builder.gui.main_window import MainWindow
from universal_dataset_builder.gui.pages.dataset import DatasetPage
from universal_dataset_builder.gui.styles.theme_manager import ThemeManager
from universal_dataset_builder.storage.database import read_images


def _application():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_main_window_builds_navigation_and_switches_theme(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    application = _application()

    window = MainWindow()
    assert window.pages.count() == 6
    assert len(window.navigation_buttons) == 6
    assert window.windowTitle() == "Universal Dataset Builder"
    assert window.centralWidget().objectName() == "CentralWidget"
    assert isinstance(window.pages.widget(1), type(window.dataset_page))

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
    assert "QMainWindow, #CentralWidget, QMenuBar, QMenu { background-color: #17191d; }" in dark
    assert "QMainWindow, #CentralWidget, QMenuBar, QMenu { background-color: #f5f6f8; }" in light


def test_dataset_browser_shows_images_and_saves_captions(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    application = _application()

    project = Project.create(tmp_path / "dataset-project", "Browser test")
    Image.new("RGB", (80, 50), "navy").save(project.source_path / "wolf.png")
    scan_directory(project.path, project.source_path)

    page = DatasetPage()
    page.resize(900, 650)
    page.set_project(project)

    assert page.gallery.count() == 1
    assert page._selected_image_id is not None
    assert not page.gallery.item(0).icon().isNull()

    page.caption_editor.setPlainText("A gray anthropomorphic wolf with blue eyes.")
    page.save_caption()

    image = read_images(project.path)[0]
    assert image["caption_text"] == "A gray anthropomorphic wolf with blue eyes."
    assert image["status"] == "Reviewed"
    assert image["caption_reviewed"] == 1

    page.status_filter.setCurrentIndex(page.status_filter.findData("Excluded"))
    assert page.gallery.count() == 0
    page.status_filter.setCurrentIndex(page.status_filter.findData("Reviewed"))
    assert page.gallery.count() == 1

    page.close()
    application.processEvents()
