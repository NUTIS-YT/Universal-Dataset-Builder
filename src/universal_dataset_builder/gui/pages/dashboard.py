"""Project dashboard page."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from universal_dataset_builder.core.project import Project


class DashboardPage(QWidget):
    """Show project status and the main onboarding actions."""

    new_project_requested = Signal()
    open_project_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        self.heading = QLabel("Welcome to Universal Dataset Builder")
        self.heading.setObjectName("SectionTitle")
        layout.addWidget(self.heading)

        self.description = QLabel(
            "Create a project to organize source images, normalized files, and training captions."
        )
        self.description.setObjectName("MutedText")
        self.description.setWordWrap(True)
        layout.addWidget(self.description)

        cards = QGridLayout()
        cards.setSpacing(14)
        self.counters: dict[str, QLabel] = {}
        for index, (key, title) in enumerate(
            (
                ("images", "Images"),
                ("captions", "Captions"),
                ("reviewed", "Reviewed"),
                ("failed", "Failed"),
            )
        ):
            card = QFrame()
            card.setObjectName("StatCard")
            card_layout = QVBoxLayout(card)
            value = QLabel("—")
            value.setObjectName("StatValue")
            label = QLabel(title)
            label.setObjectName("MutedText")
            card_layout.addWidget(value)
            card_layout.addWidget(label)
            cards.addWidget(card, index // 2, index % 2)
            self.counters[key] = value
        layout.addLayout(cards)

        self.empty_state = QFrame()
        self.empty_state.setObjectName("EmptyState")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_title = QLabel("No project is open")
        empty_title.setObjectName("SectionTitle")
        empty_text = QLabel(
            "Start by creating a new dataset project or opening an existing project.fdb file."
        )
        empty_text.setObjectName("MutedText")
        empty_text.setWordWrap(True)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_text)

        actions = QHBoxLayout()
        create_button = QPushButton("Create project")
        create_button.setObjectName("PrimaryButton")
        create_button.clicked.connect(self.new_project_requested.emit)
        open_button = QPushButton("Open project")
        open_button.clicked.connect(self.open_project_requested.emit)
        actions.addWidget(create_button)
        actions.addWidget(open_button)
        actions.addStretch(1)
        empty_layout.addLayout(actions)
        layout.addWidget(self.empty_state)
        layout.addStretch(1)
        self.set_project(None)

    def set_project(self, project: Project | None) -> None:
        """Refresh counters for the supplied project."""
        is_open = project is not None
        self.empty_state.setVisible(not is_open)
        self.heading.setText(project.name if project else "Welcome to Universal Dataset Builder")
        self.description.setText(
            f"Project location: {project.path.parent}"
            if project
            else "Create a project to organize source images, normalized files, and training captions."
        )
        if project is None:
            for counter in self.counters.values():
                counter.setText("—")
            return

        stats = project.statistics()
        for key, counter in self.counters.items():
            counter.setText(str(stats[key]))
