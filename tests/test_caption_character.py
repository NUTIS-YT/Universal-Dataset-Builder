from __future__ import annotations

import json

from fastapi.testclient import TestClient
from PIL import Image

from universal_dataset_builder.api.app import create_app
from universal_dataset_builder.core.config import ConfigStore
from universal_dataset_builder.core.project import Project
from universal_dataset_builder.services import caption_service
from universal_dataset_builder.services.caption_service import prepend_trigger_word
from universal_dataset_builder.storage.database import (
    connect,
    read_caption_character_settings,
    read_images,
    save_caption_character_settings,
)


def test_character_settings_round_trip_with_project_file(tmp_path):
    project = Project.create(tmp_path / "dataset-a", "Dataset A")
    settings = save_caption_character_settings(
        project.path,
        enabled=True,
        description="A dark-furred fox with amber eyes and a white chest.",
        trigger_word="amber_fox",
    )

    reopened = Project.open(project.path)

    assert read_caption_character_settings(reopened.path) == settings
    assert settings == {
        "enabled": True,
        "description": "A dark-furred fox with amber eyes and a white chest.",
        "trigger_word": "amber_fox",
    }

    other_project = Project.create(tmp_path / "dataset-b", "Dataset B")
    assert read_caption_character_settings(other_project.path) == {
        "enabled": False,
        "description": "",
        "trigger_word": "",
    }


def test_caption_generation_uses_character_context_and_prepends_trigger(
    tmp_path,
    monkeypatch,
):
    project = Project.create(tmp_path / "character-dataset", "Character Dataset")
    source_image = project.source_path / "view.png"
    Image.new("RGB", (32, 24), "purple").save(source_image)

    normalized_image = project.dataset_path / "00001.png"
    Image.new("RGB", (32, 24), "purple").save(normalized_image)
    with connect(project.path) as connection:
        connection.execute(
            """
            INSERT INTO images (
                filename, original_filename, original_path, normalized_path, status
            ) VALUES (?, ?, ?, ?, 'Pending')
            """,
            ("00001.png", "view.png", str(source_image), str(normalized_image)),
        )
        connection.commit()

    save_caption_character_settings(
        project.path,
        enabled=True,
        description="A white-haired character with blue eyes and a small star marking.",
        trigger_word="star_character",
    )

    prompts: list[str] = []

    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def caption_image(self, _image_path, prompt, _model):
            prompts.append(prompt)
            return "A white-haired character looking over one shoulder."

    monkeypatch.setattr(caption_service, "OpenAICompatibleClient", FakeClient)

    result = caption_service.CaptionGenerationService.generate(
        project.path,
        project.source_path,
        project.dataset_path,
        base_url="http://127.0.0.1:8080/v1",
        api_key="",
        timeout_seconds=30,
        model="test-vlm",
        prompt="Describe the visible image.",
        selection_mode="missing",
        limit=0,
    )

    image = read_images(project.path)[0]
    assert result.generated == 1
    assert result.failed == 0
    assert "A white-haired character with blue eyes" in prompts[0]
    assert "different viewpoints" in prompts[0]
    assert "Do not include it in your response." in prompts[0]
    assert image["caption_text"] == (
        "star_character, A white-haired character looking over one shoulder."
    )

    manifest = json.loads(project.metadata_path.read_text(encoding="utf-8").strip())
    assert manifest["prompt"] == image["caption_text"]


def test_character_reference_can_be_disabled_without_deleting_saved_values(tmp_path, monkeypatch):
    project = Project.create(tmp_path / "disabled-dataset", "Disabled Dataset")
    source_image = project.source_path / "view.png"
    Image.new("RGB", (16, 16), "black").save(source_image)

    normalized_image = project.dataset_path / "00001.png"
    Image.new("RGB", (16, 16), "black").save(normalized_image)
    with connect(project.path) as connection:
        connection.execute(
            """
            INSERT INTO images (
                filename, original_filename, original_path, normalized_path, status
            ) VALUES (?, ?, ?, ?, 'Pending')
            """,
            ("00001.png", "view.png", str(source_image), str(normalized_image)),
        )
        connection.commit()

    save_caption_character_settings(
        project.path,
        enabled=False,
        description="Keep this stored for later.",
        trigger_word="remember_me",
    )

    prompts: list[str] = []

    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def caption_image(self, _image_path, prompt, _model):
            prompts.append(prompt)
            return "A small character standing in a room."

    monkeypatch.setattr(caption_service, "OpenAICompatibleClient", FakeClient)
    caption_service.CaptionGenerationService.generate(
        project.path,
        project.source_path,
        project.dataset_path,
        base_url="http://127.0.0.1:8080/v1",
        api_key="",
        timeout_seconds=30,
        model="test-vlm",
        prompt="Describe the visible image.",
        selection_mode="missing",
        limit=0,
    )

    assert prompts == ["Describe the visible image."]
    assert read_images(project.path)[0]["caption_text"] == (
        "A small character standing in a room."
    )
    saved = read_caption_character_settings(project.path)
    assert saved["description"] == "Keep this stored for later."
    assert saved["trigger_word"] == "remember_me"


def test_api_reads_and_updates_project_character_settings(tmp_path):
    config = ConfigStore(tmp_path / "config.json")
    with TestClient(
        create_app(config_store=config),
        base_url="http://127.0.0.1",
    ) as client:
        created = client.post(
            "/api/v1/project/create",
            json={"directory": str(tmp_path), "name": "API Character"},
        )
        assert created.status_code == 201

        initial = client.get("/api/v1/project/caption-settings")
        assert initial.status_code == 200
        assert initial.json() == {
            "enabled": False,
            "description": "",
            "trigger_word": "",
        }

        updated = client.put(
            "/api/v1/project/caption-settings",
            json={
                "enabled": True,
                "description": "A character with silver hair and a red scarf.",
                "trigger_word": "silver_scarf",
            },
        )
        assert updated.status_code == 200
        assert updated.json() == {
            "enabled": True,
            "description": "A character with silver hair and a red scarf.",
            "trigger_word": "silver_scarf",
        }
        assert client.get("/api/v1/project/caption-settings").json() == updated.json()

        database_path = tmp_path / "API Character" / "project.fdb"
        assert Project.open(database_path).path == database_path
        assert read_caption_character_settings(database_path) == updated.json()



def test_prepend_trigger_word_does_not_duplicate_existing_prefix():
    assert prepend_trigger_word(
        "star_character, A white-haired character.",
        "star_character",
    ) == "star_character, A white-haired character."
