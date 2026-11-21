"""Application settings page."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QVBoxLayout, QWidget


class SettingsPage(QWidget):
    """Expose user preferences that are already implemented."""

    theme_changed = Signal(str)

    def __init__(self, current_theme: str = "dark") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title = QLabel("Application settings")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        description = QLabel("Preferences are stored locally on this computer.")
        description.setObjectName("MutedText")
        layout.addWidget(description)

        form = QFormLayout()
        self.theme_selector = QComboBox()
        self.theme_selector.addItem("Dark", "dark")
        self.theme_selector.addItem("Light", "light")
        index = self.theme_selector.findData(current_theme)
        self.theme_selector.setCurrentIndex(max(index, 0))
        self.theme_selector.currentIndexChanged.connect(self._emit_theme)
        form.addRow("Appearance", self.theme_selector)
        layout.addLayout(form)
        layout.addStretch(1)

    def _emit_theme(self) -> None:
        theme = self.theme_selector.currentData()
        if isinstance(theme, str):
            self.theme_changed.emit(theme)
