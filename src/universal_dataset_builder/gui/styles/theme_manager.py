"""Built-in light and dark Qt stylesheets."""

from __future__ import annotations


class ThemeManager:
    """Return the stylesheet associated with an application theme."""

    DARK = """
    QWidget {
        background-color: #17191d;
        color: #e8eaf0;
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 10pt;
    }
    QMainWindow, QMenuBar, QMenu { background-color: #17191d; }
    #Sidebar { background-color: #202329; border-right: 1px solid #30343c; }
    #Brand { color: #f5f6fa; font-size: 17pt; font-weight: 700; }
    #NavigationButton {
        text-align: left; padding: 11px 13px; border: 0; border-radius: 8px;
        background: transparent; color: #b9bec9;
    }
    #NavigationButton:hover { background: #2b3038; color: #ffffff; }
    #NavigationButton:checked { background: #343b47; color: #ffffff; font-weight: 600; }
    #PageTitle { font-size: 18pt; font-weight: 650; }
    #SectionTitle { font-size: 15pt; font-weight: 650; }
    #MutedText, #SidebarProject { color: #a0a7b4; }
    #StatCard, #EmptyState {
        background: #22262d; border: 1px solid #343a44; border-radius: 12px;
    }
    #StatValue { font-size: 25pt; font-weight: 700; color: #f3f5f8; }
    QPushButton {
        padding: 9px 14px; border: 1px solid #414854; border-radius: 8px;
        background: #292e36;
    }
    QPushButton:hover { background: #343b46; }
    #PrimaryButton { background: #536b91; border-color: #536b91; color: white; font-weight: 600; }
    #PrimaryButton:hover { background: #627da8; }
    QComboBox, QLineEdit, QTextEdit {
        padding: 8px; border: 1px solid #414854; border-radius: 7px;
        background: #22262d;
    }
    QMenu::item { padding: 6px 24px; }
    QMenu::item:selected { background: #343b47; }
    """

    LIGHT = """
    QWidget {
        background-color: #f5f6f8;
        color: #20242b;
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 10pt;
    }
    QMainWindow, QMenuBar, QMenu { background-color: #f5f6f8; }
    #Sidebar { background-color: #ffffff; border-right: 1px solid #e2e5ea; }
    #Brand { color: #20242b; font-size: 17pt; font-weight: 700; }
    #NavigationButton {
        text-align: left; padding: 11px 13px; border: 0; border-radius: 8px;
        background: transparent; color: #555e6b;
    }
    #NavigationButton:hover { background: #edf0f4; color: #20242b; }
    #NavigationButton:checked { background: #e2e8f1; color: #243c5d; font-weight: 600; }
    #PageTitle { font-size: 18pt; font-weight: 650; }
    #SectionTitle { font-size: 15pt; font-weight: 650; }
    #MutedText, #SidebarProject { color: #687281; }
    #StatCard, #EmptyState {
        background: #ffffff; border: 1px solid #e1e5eb; border-radius: 12px;
    }
    #StatValue { font-size: 25pt; font-weight: 700; color: #20242b; }
    QPushButton {
        padding: 9px 14px; border: 1px solid #d1d7e0; border-radius: 8px;
        background: #ffffff;
    }
    QPushButton:hover { background: #edf0f4; }
    #PrimaryButton { background: #365d91; border-color: #365d91; color: white; font-weight: 600; }
    #PrimaryButton:hover { background: #436fa9; }
    QComboBox, QLineEdit, QTextEdit {
        padding: 8px; border: 1px solid #d1d7e0; border-radius: 7px;
        background: #ffffff;
    }
    QMenu::item { padding: 6px 24px; }
    QMenu::item:selected { background: #e2e8f1; }
    """

    @classmethod
    def stylesheet(cls, theme: str) -> str:
        """Return the dark theme unless light was explicitly requested."""
        return cls.LIGHT if theme == "light" else cls.DARK
