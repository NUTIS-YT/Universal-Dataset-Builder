"""Consistent placeholder page for features delivered in later milestones."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    """Explain the purpose and current availability of an upcoming feature."""

    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        heading = QLabel(title)
        heading.setObjectName("SectionTitle")
        layout.addWidget(heading)

        summary = QLabel(description)
        summary.setObjectName("MutedText")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        panel = QFrame()
        panel.setObjectName("EmptyState")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 24, 24, 24)
        status = QLabel("Planned for a future milestone")
        status.setObjectName("SectionTitle")
        detail = QLabel(
            "This section will become available as its processing and review "
            "workflow is implemented."
        )
        detail.setObjectName("MutedText")
        detail.setWordWrap(True)
        panel_layout.addWidget(status)
        panel_layout.addWidget(detail)
        layout.addWidget(panel)
        layout.addStretch(1)
