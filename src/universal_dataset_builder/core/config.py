"""Persistent, user-local application settings."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_CAPTION_PROMPT = (
    "Describe the image accurately and concisely in English for an image-training dataset. "
    "Focus on the main subject, visible appearance, clothing, pose, action, setting, "
    "composition, and notable visual details. Do not guess identities, hidden details, "
    "or facts that are not supported by the image. Return only the caption, without "
    "a preamble or quotation marks."
)

DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "recent_project": None,
    "vlm_base_url": "http://127.0.0.1:8080/v1",
    "vlm_api_key": "",
    "vlm_model": "",
    "vlm_models": [],
    "vlm_timeout": 120,
    "caption_prompt": DEFAULT_CAPTION_PROMPT,
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
        """Load known settings while ignoring invalid values and unknown keys."""
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

        for key in ("vlm_base_url", "vlm_api_key", "vlm_model", "caption_prompt"):
            value = payload.get(key)
            if isinstance(value, str):
                self._values[key] = value[:20_000]

        models = payload.get("vlm_models")
        if isinstance(models, list):
            self._values["vlm_models"] = [
                item[:512]
                for item in models[:500]
                if isinstance(item, str) and item.strip()
            ]

        timeout = payload.get("vlm_timeout")
        if isinstance(timeout, int) and not isinstance(timeout, bool):
            if 5 <= timeout <= 600:
                self._values["vlm_timeout"] = timeout

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
        if key == "vlm_timeout":
            if not isinstance(value, int) or isinstance(value, bool) or not 5 <= value <= 600:
                raise ValueError("VLM timeout must be between 5 and 600 seconds.")
        if key in {"vlm_base_url", "vlm_api_key", "vlm_model", "caption_prompt"}:
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a string.")
            if len(value) > 20_000:
                raise ValueError(f"{key} is too long.")
        if key == "vlm_models":
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                raise ValueError("VLM models must be a list of strings.")
        self._values[key] = value

    def save(self) -> None:
        """Write settings atomically and restrict access to the local config file."""
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
            if os.name != "nt":
                self.path.chmod(0o600)
        except Exception:
            Path(temporary_name).unlink(missing_ok=True)
            raise
