from __future__ import annotations

import os
import stat

import pytest

from universal_dataset_builder.core.config import ConfigStore


def test_config_uses_defaults_when_file_does_not_exist(tmp_path):
    store = ConfigStore(tmp_path / "config.json")

    assert store.get("theme") == "dark"
    assert store.get("recent_project") is None
    assert store.get("vlm_base_url") == "http://127.0.0.1:8080/v1"
    assert store.get("vlm_api_key") == ""
    assert store.get("vlm_models") == []


def test_config_round_trips_values(tmp_path):
    path = tmp_path / "nested" / "config.json"
    store = ConfigStore(path)
    store.set("theme", "light")
    store.set("recent_project", "/tmp/example/project.fdb")
    store.set("vlm_base_url", "http://localhost:8080/v1")
    store.set("vlm_api_key", "test-token")
    store.set("vlm_model", "qwen-vl")
    store.set("vlm_models", ["qwen-vl", "llava"])
    store.set("vlm_timeout", 90)
    store.set("caption_prompt", "Describe this image.")
    store.save()

    loaded = ConfigStore(path)
    assert loaded.get("theme") == "light"
    assert loaded.get("recent_project") == "/tmp/example/project.fdb"
    assert loaded.get("vlm_base_url") == "http://localhost:8080/v1"
    assert loaded.get("vlm_api_key") == "test-token"
    assert loaded.get("vlm_model") == "qwen-vl"
    assert loaded.get("vlm_models") == ["qwen-vl", "llava"]
    assert loaded.get("vlm_timeout") == 90
    assert loaded.get("caption_prompt") == "Describe this image."

    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_config_ignores_invalid_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid", encoding="utf-8")

    store = ConfigStore(path)

    assert store.get("theme") == "dark"
    assert store.get("recent_project") is None


def test_config_rejects_unknown_theme_and_invalid_timeout(tmp_path):
    store = ConfigStore(tmp_path / "config.json")

    with pytest.raises(ValueError):
        store.set("theme", "neon")
    with pytest.raises(ValueError):
        store.set("vlm_timeout", 1000)
