"""Main window and application navigation."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from universal_dataset_builder.core.config import ConfigStore
from universal_dataset_builder.core.project import Project
from universal_dataset_builder.dataset.metadata import JSONL_METADATA_FORMAT
from universal_dataset_builder.gui.pages.caption_generator import CaptionGeneratorPage
from universal_dataset_builder.gui.pages.dashboard import DashboardPage
from universal_dataset_builder.gui.pages.dataset import DatasetPage
from universal_dataset_builder.gui.pages.normalizer import NormalizerPage
from universal_dataset_builder.gui.pages.settings import SettingsPage
from universal_dataset_builder.gui.pages.vlm_connection import VLMConnectionPage
from universal_dataset_builder.gui.styles.theme_manager import ThemeManager

LOGGER = logging.getLogger(__name__)


class ProjectCreationDialog(QDialog):
    """Collect the project name and training metadata format."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create project")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My dataset")
        form.addRow("Project name", self.name_edit)

        self.metadata_format_selector = QComboBox()
        self.metadata_format_selector.addItem("JSON Lines (.jsonl)", JSONL_METADATA_FORMAT)
        self.metadata_format_selector.setObjectName("MetadataFormatSelector")
        form.addRow("Training metadata format", self.metadata_format_selector)

        layout.addLayout(form)
        note = QLabel("JSONL is currently the only supported metadata format.")
        note.setObjectName("MutedText")
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def metadata_format(self) -> str:
        """Return the selected project metadata format."""
        return str(self.metadata_format_selector.currentData())


class MainWindow(QMainWindow):
    """Primary application window."""

    NAV_ITEMS = (
        ("Dashboard", "Overview and project status"),
        ("Dataset", "Browse images and captions"),
        ("Normalizer", "Convert images to a consistent format"),
        ("Caption Generator", "Generate captions through a VLM API"),
        ("VLM Connection", "Configure an external vision API"),
        ("Settings", "Application preferences"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.config = ConfigStore()
        self.project: Project | None = None
        self.setMinimumSize(980, 640)
        self.resize(1180, 760)
        self.setWindowTitle("Universal Dataset Builder")

        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(232)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 24, 18, 18)
        sidebar_layout.setSpacing(8)

        brand = QLabel("Universal\nDataset Builder")
        brand.setObjectName("Brand")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addSpacing(22)

        self.navigation_buttons: list[QPushButton] = []
        for index, (title, _description) in enumerate(self.NAV_ITEMS):
            button = QPushButton(title)
            button.setObjectName("NavigationButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, page=index: self.show_page(page))
            sidebar_layout.addWidget(button)
            self.navigation_buttons.append(button)

        sidebar_layout.addStretch(1)
        self.project_label = QLabel("No project open")
        self.project_label.setObjectName("SidebarProject")
        self.project_label.setWordWrap(True)
        sidebar_layout.addWidget(self.project_label)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 22, 28, 22)
        content_layout.setSpacing(18)

        header = QHBoxLayout()
        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("PageTitle")
        header.addWidget(self.page_title)
        header.addStretch(1)
        self.project_status = QLabel("No project")
        self.project_status.setObjectName("MutedText")
        header.addWidget(self.project_status)
        content_layout.addLayout(header)

        self.pages = QStackedWidget()
        self.dashboard = DashboardPage()
        self.dashboard.new_project_requested.connect(self.create_project)
        self.dashboard.open_project_requested.connect(self.open_project_dialog)
        self.pages.addWidget(self.dashboard)

        self.dataset_page = DatasetPage()
        self.dataset_page.scan_completed.connect(self._refresh_dashboard)
        self.pages.addWidget(self.dataset_page)

        self.normalizer_page = NormalizerPage()
        self.normalizer_page.normalization_completed.connect(self._refresh_dashboard)
        self.normalizer_page.normalization_completed.connect(self.dataset_page.refresh)
        self.pages.addWidget(self.normalizer_page)

        self.caption_generator_page = CaptionGeneratorPage(self.config)
        self.caption_generator_page.generation_completed.connect(self._refresh_dashboard)
        self.caption_generator_page.generation_completed.connect(self.dataset_page.refresh)
        self.pages.addWidget(self.caption_generator_page)

        self.vlm_connection_page = VLMConnectionPage(self.config)
        self.vlm_connection_page.connection_saved.connect(
            self.caption_generator_page.refresh_connection
        )
        self.pages.addWidget(self.vlm_connection_page)

        self.settings_page = SettingsPage(self.config.get("theme", "dark"))
        self.settings_page.theme_changed.connect(self.apply_theme)
        self.pages.addWidget(self.settings_page)
        content_layout.addWidget(self.pages, 1)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)
        self._create_menu()
        self.show_page(0)
        self.apply_theme(self.config.get("theme", "dark"))
        self._restore_recent_project()

    def _create_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        new_action = QAction("New Project…", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.create_project)
        file_menu.addAction(new_action)

        open_action = QAction("Open Project…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project_dialog)
        file_menu.addAction(open_action)

        file_menu.addSeparator()
        close_action = QAction("Close Project", self)
        close_action.triggered.connect(self.close_project)
        file_menu.addAction(close_action)

    def show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.page_title.setText(self.NAV_ITEMS[index][0])
        for button_index, button in enumerate(self.navigation_buttons):
            button.setChecked(button_index == index)

    def apply_theme(self, theme: str) -> None:
        if theme not in {"dark", "light"}:
            theme = "dark"
        self.config.set("theme", theme)
        self.config.save()
        self.setStyleSheet(ThemeManager.stylesheet(theme))

    def create_project(self) -> None:
        dialog = ProjectCreationDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        clean_name = dialog.name_edit.text().strip()
        if (
            not clean_name
            or clean_name in {".", ".."}
            or "/" in clean_name
            or "\\" in clean_name
        ):
            QMessageBox.warning(self, "Invalid project name", "Enter a valid project name.")
            return

        parent_directory = QFileDialog.getExistingDirectory(
            self,
            "Choose project location",
            str(Path.home()),
        )
        if not parent_directory:
            return

        try:
            project = Project.create(
                Path(parent_directory) / clean_name,
                clean_name,
                metadata_format=dialog.metadata_format,
            )
            self._set_project(project)
            QMessageBox.information(
                self,
                "Project created",
                f"Project '{project.name}' was created successfully.\n"
                f"Training metadata: {project.metadata_path.name}",
            )
        except (OSError, ValueError) as error:
            LOGGER.exception("Could not create project")
            QMessageBox.critical(self, "Could not create project", str(error))

    def open_project_dialog(self) -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open project",
            str(Path.home()),
            "Universal Dataset Builder project (project.fdb);;All files (*)",
        )
        if filename:
            self._open_project(Path(filename))

    def _open_project(self, path: Path) -> None:
        try:
            self._set_project(Project.open(path))
        except (OSError, ValueError) as error:
            LOGGER.exception("Could not open project")
            QMessageBox.critical(self, "Could not open project", str(error))

    def _set_project(self, project: Project) -> None:
        self.project = project
        self.dashboard.set_project(project)
        self.dataset_page.set_project(project)
        self.normalizer_page.set_project(project)
        self.caption_generator_page.set_project(project)
        self.project_label.setText(project.name)
        self.project_status.setText(project.name)
        self.setWindowTitle(f"{project.name} — Universal Dataset Builder")
        self.config.set("recent_project", str(project.path))
        self.config.save()
        self.show_page(0)

    def close_project(self) -> None:
        self.project = None
        self.dashboard.set_project(None)
        self.dataset_page.set_project(None)
        self.normalizer_page.set_project(None)
        self.caption_generator_page.set_project(None)
        self.project_label.setText("No project open")
        self.project_status.setText("No project")
        self.setWindowTitle("Universal Dataset Builder")
        self.config.set("recent_project", None)
        self.config.save()

    def _refresh_dashboard(self) -> None:
        if self.project is not None:
            self.dashboard.set_project(self.project)

    def _restore_recent_project(self) -> None:
        recent_project = self.config.get("recent_project")
        if recent_project and Path(recent_project).is_file():
            self._open_project(Path(recent_project))
