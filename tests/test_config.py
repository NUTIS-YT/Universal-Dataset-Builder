from __future__ import annotations

import pytest

from universal_dataset_builder.core.config import ConfigStore


def test_config_uses_defaults_when_file_does_not_exist(tmp_path):
    store = ConfigStore(tmp_path / "config.json")

    assert store.get("theme") == "dark"
    assert store.get("recent_project") is None


def test_config_round_trips_values(tmp_path):
    path = tmp_path / "nested" / "config.json"
    store = ConfigStore(path)
    store.set("theme", "light")
    store.set("recent_project", "/tmp/example/project.fdb")
    store.save()

    loaded = ConfigStore(path)
    assert loaded.get("theme") == "light"
    assert loaded.get("recent_project") == "/tmp/example/project.fdb"


def test_config_ignores_invalid_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid", encoding="utf-8")

    store = ConfigStore(path)

    assert store.get("theme") == "dark"
    assert store.get("recent_project") is None


def test_config_rejects_unknown_theme(tmp_path):
    store = ConfigStore(tmp_path / "config.json")

    with pytest.raises(ValueError):
        store.set("theme", "neon")
