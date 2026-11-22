"""Desktop launcher for the Legacy and Expressive interfaces."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from universal_dataset_builder.core.config import get_config_directory

API_BASE_URL = "http://127.0.0.1:17891"
API_HEALTH_URL = f"{API_BASE_URL}/api/v1/health"


class LauncherDialog(QDialog):
    """Let the user choose which desktop interface to open."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selected_mode: str | None = None
        self.setWindowTitle("Universal Dataset Builder")
        self.setMinimumWidth(520)
        self.setObjectName("LauncherDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 22)
        layout.setSpacing(12)

        title = QLabel("Choose your workspace")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Select the interface you want to use. Both versions work with the same "
            "project files and Python services."
        )
        subtitle.setObjectName("MutedText")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        legacy_button = QPushButton("Legacy · PySide6")
        legacy_button.setObjectName("LegacyLaunchButton")
        legacy_button.setMinimumHeight(54)
        legacy_button.clicked.connect(
            lambda _checked=False: self._choose("legacy")
        )
        layout.addWidget(legacy_button)

        legacy_note = QLabel("The existing, established desktop interface.")
        legacy_note.setObjectName("MutedText")
        layout.addWidget(legacy_note)
        layout.addSpacing(8)

        expressive_button = QPushButton("Expressive UI Beta · Flutter")
        expressive_button.setObjectName("ExpressiveLaunchButton")
        expressive_button.setMinimumHeight(58)
        expressive_button.clicked.connect(
            lambda _checked=False: self._choose("expressive")
        )
        layout.addWidget(expressive_button)

        expressive_note = QLabel(
            "The new Material 3 interface. The launcher starts its local API "
            "automatically and prepares the Flutter desktop runner when needed."
        )
        expressive_note.setObjectName("MutedText")
        expressive_note.setWordWrap(True)
        layout.addWidget(expressive_note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(8)
        layout.addWidget(buttons)

    @property
    def selected_mode(self) -> str | None:
        """Return 'legacy', 'expressive', or None when the dialog was cancelled."""
        return self._selected_mode

    def _choose(self, mode: str) -> None:
        self._selected_mode = mode
        self.accept()


def _api_is_ready(timeout_seconds: float = 0.5) -> bool:
    """Return True only when the expected UDB health endpoint responds."""
    request = urllib.request.Request(
        API_HEALTH_URL,
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status == 200 and payload.get("status") == "ok"
    except (
        OSError,
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        AttributeError,
    ):
        return False


def start_api_server(
    *,
    startup_timeout_seconds: float = 15.0,
) -> tuple[subprocess.Popen[bytes] | None, str | None]:
    """Start the API only when it is not already running.

    The returned process is owned by the caller and may be stopped after the UI
    exits. If an API server was already running, the process value is None.
    """
    if _api_is_ready():
        return None, None

    log_path = get_config_directory() / "logs" / "api.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "universal_dataset_builder.api.server",
    ]
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    try:
        with log_path.open("ab") as log_stream:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log_stream,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
            )
    except OSError as error:
        return None, f"Could not start the local API: {error}"

    deadline = time.monotonic() + startup_timeout_seconds
    while time.monotonic() < deadline:
        if _api_is_ready():
            return process, None
        exit_code = process.poll()
        if exit_code is not None:
            return (
                None,
                f"The local API exited with code {exit_code}. "
                f"See the log file: {log_path}",
            )
        time.sleep(0.25)

    stop_api_server(process)
    return (
        None,
        f"The local API did not become ready within "
        f"{startup_timeout_seconds:.0f} seconds. See: {log_path}",
    )


def stop_api_server(process: subprocess.Popen[bytes] | None) -> None:
    """Stop only the API process started by this launcher."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def build_flutter_command(
    executable: str,
    arguments: list[str],
    *,
    windows: bool | None = None,
) -> list[str]:
    """Build a subprocess command that also supports Windows Flutter batch files."""
    is_windows = os.name == "nt" if windows is None else windows
    if is_windows and Path(executable).suffix.casefold() in {".bat", ".cmd"}:
        command_line = subprocess.list2cmdline([executable, *arguments])
        return [
            os.environ.get("COMSPEC", "cmd.exe"),
            "/d",
            "/s",
            "/c",
            command_line,
        ]
    return [executable, *arguments]


def _run_flutter_step(
    executable: str,
    arguments: list[str],
    app_directory: Path,
    *,
    step_name: str,
) -> bool:
    command = build_flutter_command(executable, arguments)
    try:
        completed = subprocess.run(command, cwd=app_directory, check=False)
    except OSError as error:
        QMessageBox.critical(
            None,
            "Expressive UI could not start",
            f"Could not run Flutter during '{step_name}': {error}",
        )
        return False

    if completed.returncode != 0:
        QMessageBox.critical(
            None,
            "Expressive UI could not start",
            f"Flutter step '{step_name}' failed with exit code "
            f"{completed.returncode}. Check the terminal output.",
        )
        return False
    return True


def launch_expressive_ui() -> int:
    """Prepare the local Flutter desktop runner and launch Expressive UI."""
    flutter = shutil.which("flutter")
    if flutter is None:
        QMessageBox.critical(
            None,
            "Flutter SDK not found",
            "Install Flutter, add its bin directory to PATH, and reopen the launcher.",
        )
        return 1

    if sys.platform == "win32":
        platform = "windows"
    elif sys.platform.startswith("linux"):
        platform = "linux"
    else:
        QMessageBox.critical(
            None,
            "Unsupported desktop platform",
            "The Expressive desktop runner is currently configured for Linux and Windows.",
        )
        return 1

    repository_root = Path(__file__).resolve().parents[3]
    app_directory = repository_root / "flutter_app"
    if not (app_directory / "pubspec.yaml").is_file():
        QMessageBox.critical(
            None,
            "Flutter project not found",
            f"Could not find the Flutter project at: {app_directory}",
        )
        return 1

    if not (app_directory / platform).is_dir():
        create_arguments = [
            "create",
            "--platforms",
            platform,
            "--project-name",
            "universal_dataset_builder_expressive",
            "--org",
            "com.ericnorthwest",
            "--no-pub",
            ".",
        ]
        if not _run_flutter_step(
            flutter,
            create_arguments,
            app_directory,
            step_name="creating the desktop runner",
        ):
            return 1

    if not _run_flutter_step(
        flutter,
        ["pub", "get"],
        app_directory,
        step_name="installing Flutter dependencies",
    ):
        return 1

    command = build_flutter_command(flutter, ["run", "-d", platform])
    try:
        return subprocess.run(command, cwd=app_directory, check=False).returncode
    except OSError as error:
        QMessageBox.critical(
            None,
            "Expressive UI could not start",
            f"Could not launch Flutter: {error}",
        )
        return 1
