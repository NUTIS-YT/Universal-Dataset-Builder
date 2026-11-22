from __future__ import annotations

from PySide6.QtWidgets import QApplication, QPushButton

from universal_dataset_builder.gui.launcher import (
    LauncherDialog,
    build_flutter_command,
)


def _application(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_launcher_dialog_selects_legacy_mode(monkeypatch):
    application = _application(monkeypatch)
    dialog = LauncherDialog()

    button = dialog.findChild(QPushButton, "LegacyLaunchButton")
    assert button is not None
    button.click()

    assert dialog.selected_mode == "legacy"
    assert dialog.result() == dialog.DialogCode.Accepted
    dialog.close()
    application.processEvents()


def test_launcher_dialog_selects_expressive_mode(monkeypatch):
    application = _application(monkeypatch)
    dialog = LauncherDialog()

    button = dialog.findChild(QPushButton, "ExpressiveLaunchButton")
    assert button is not None
    button.click()

    assert dialog.selected_mode == "expressive"
    assert dialog.result() == dialog.DialogCode.Accepted
    dialog.close()
    application.processEvents()


def test_flutter_command_supports_windows_batch_files():
    command = build_flutter_command(
        r"C:\tools\flutter\bin\flutter.bat",
        ["run", "-d", "windows"],
        windows=True,
    )

    assert command[:4] == ["cmd.exe", "/d", "/s", "/c"]
    assert "flutter.bat" in command[4]
    assert "run" in command[4]
    assert "windows" in command[4]


def test_flutter_command_uses_direct_executable_on_linux():
    assert build_flutter_command(
        "/opt/flutter/bin/flutter",
        ["pub", "get"],
        windows=False,
    ) == ["/opt/flutter/bin/flutter", "pub", "get"]
