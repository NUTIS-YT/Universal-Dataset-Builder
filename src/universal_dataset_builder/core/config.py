"""Persistent, user-local application settings."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "recent_project": None,
}


def get_config_directory() -> Path:
    """Return the platform-appropriate user configuration directory."""
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "Universal Dataset Builder"
        return Path.home() / "AppData" / "Roaming" / "Universal Dataset Builder"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Universal Dataset Builder"

    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / "universal-dataset-builder"


class ConfigStore:
    """Read and atomically write application settings as JSON."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else get_config_directory() / "config.json"
        self._values = DEFAULTS.copy()
        self.load()

    def load(self) -> dict[str, Any]:
        """Load settings, falling back to safe defaults for invalid files."""
        self._values = DEFAULTS.copy()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return self.values
        except (OSError, json.JSONDecodeError):
            return self.values

        if not isinstance(payload, dict):
            return self.values

        theme = payload.get("theme")
        if isinstance(theme, str) and theme in {"dark", "light"}:
            self._values["theme"] = theme

        recent_project = payload.get("recent_project")
        if isinstance(recent_project, str) and recent_project.strip():
            self._values["recent_project"] = recent_project
        return self.values

    @property
    def values(self) -> dict[str, Any]:
        """Return a copy so callers cannot mutate internal state accidentally."""
        return self._values.copy()

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key == "theme" and (not isinstance(value, str) or value not in {"dark", "light"}):
            raise ValueError("Theme must be 'dark' or 'light'.")
        self._values[key] = value

    def save(self) -> None:
        """Write settings atomically to avoid partially-written JSON files."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(self._values, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
            Path(temporary_name).replace(self.path)
        except Exception:
            Path(temporary_name).unlink(missing_ok=True)
            raise
