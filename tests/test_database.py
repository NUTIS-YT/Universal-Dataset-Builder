from __future__ import annotations

import sqlite3

import pytest

from universal_dataset_builder.core.project import Project
from universal_dataset_builder.storage.database import (
    APPLICATION_ID,
    SCHEMA_VERSION,
    connect,
    read_images,
    save_generated_caption,
    save_image_caption,
    set_image_status,
)


def test_project_database_contains_expected_tables(tmp_path):
    project = Project.create(tmp_path / "dataset", "Dataset")
    with connect(project.path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert {"projects", "images", "captions", "jobs", "models", "settings"} <= tables
    assert application_id == APPLICATION_ID
    assert version == SCHEMA_VERSION


def test_caption_rows_require_a_valid_image(tmp_path):
    project = Project.create(tmp_path / "dataset", "Dataset")

    with connect(project.path) as connection:
        try:
            connection.execute(
                "INSERT INTO captions (image_id, caption_text) VALUES (999, 'caption')"
            )
            connection.commit()
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Foreign key constraint was not enforced")


def test_save_caption_marks_image_reviewed_and_replaces_previous_caption(tmp_path):
    project = Project.create(tmp_path / "dataset", "Caption test")
    with connect(project.path) as connection:
        connection.execute(
            """
            INSERT INTO images (filename, original_filename, original_path, status)
            VALUES ('wolf.png', 'wolf.png', '/source/wolf.png', 'Pending')
            """
        )
        image_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.commit()

    assert save_image_caption(project.path, image_id, "  An anthropomorphic wolf.  ") is None
    save_image_caption(project.path, image_id, "A gray anthropomorphic wolf.")

    image = read_images(project.path)[0]
    assert image["caption_text"] == "A gray anthropomorphic wolf."
    assert image["caption_reviewed"] == 1
    assert image["status"] == "Reviewed"

    with connect(project.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM captions").fetchone()[0] == 1


def test_generated_caption_is_saved_as_unreviewed_with_model_metadata(tmp_path):
    project = Project.create(tmp_path / "dataset", "Generated caption test")
    with connect(project.path) as connection:
        connection.execute(
            """
            INSERT INTO images (filename, original_filename, original_path, status)
            VALUES ('fox.png', 'fox.png', '/source/fox.png', 'Normalized')
            """
        )
        image_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.commit()

    result = save_generated_caption(
        project.path,
        image_id,
        "A red fox standing in grass.",
        model_name="qwen-vl",
        prompt_template="Describe the image.",
    )
    assert result is None

    image = read_images(project.path)[0]
    assert image["caption_text"] == "A red fox standing in grass."
    assert image["caption_reviewed"] == 0
    assert image["status"] == "Captioned"
    with connect(project.path) as connection:
        caption = connection.execute("SELECT * FROM captions").fetchone()
    assert caption["model_name"] == "qwen-vl"
    assert caption["prompt_template"] == "Describe the image."


def test_caption_cannot_be_empty_or_saved_for_unknown_image(tmp_path):
    project = Project.create(tmp_path / "dataset", "Validation test")

    with pytest.raises(ValueError, match="cannot be empty"):
        save_image_caption(project.path, 1, "  ")

    with pytest.raises(ValueError, match="does not exist"):
        save_image_caption(project.path, 999, "A caption.")


def test_status_requires_caption_for_captioned_or_reviewed(tmp_path):
    project = Project.create(tmp_path / "dataset", "Status test")
    with connect(project.path) as connection:
        connection.execute(
            """
            INSERT INTO images (filename, original_filename, original_path)
            VALUES ('fox.png', 'fox.png', '/source/fox.png')
            """
        )
        image_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.commit()

    with pytest.raises(ValueError, match="needs a caption"):
        set_image_status(project.path, image_id, "Reviewed")

    set_image_status(project.path, image_id, "Excluded")
    assert read_images(project.path)[0]["status"] == "Excluded"
