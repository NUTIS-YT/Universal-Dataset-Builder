from __future__ import annotations

import json

import pytest

from universal_dataset_builder.core.project import Project
from universal_dataset_builder.dataset.metadata import (
    read_metadata_format,
    sync_training_metadata,
)
from universal_dataset_builder.storage.database import connect


def _add_captioned_image(
    project: Project,
    relative_path: str,
    caption: str,
    *,
    status: str = "Reviewed",
    create_file: bool = True,
) -> None:
    image_path = project.dataset_path / relative_path
    if create_file:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"normalized image placeholder")

    with connect(project.path) as connection:
        connection.execute(
            """
            INSERT INTO images (
                filename, original_filename, original_path,
                normalized_path, status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                relative_path,
                image_path.name,
                str(project.source_path / image_path.name),
                str(image_path),
                status,
            ),
        )
        image_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """
            INSERT INTO captions (image_id, caption_text, reviewed)
            VALUES (?, ?, ?)
            """,
            (image_id, caption, int(status == "Reviewed")),
        )
        connection.commit()


def test_jsonl_manifest_contains_relative_image_and_prompt_fields(tmp_path):
    project = Project.create(tmp_path / "project", "JSONL test")
    _add_captioned_image(project, "00002.png", "A character says: \"Hello\".")
    _add_captioned_image(project, "nested/00001.png", "Зелёный плащ, мягкий свет.")
    _add_captioned_image(project, "00003.png", "Excluded caption.", status="Excluded")
    _add_captioned_image(project, "00004.png", "Caption for missing output.", create_file=False)

    manifest = sync_training_metadata(project.path, project.dataset_path)
    records = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
    ]

    assert manifest == project.dataset_path / "metadata.jsonl"
    assert records == [
        {"image": "00002.png", "prompt": 'A character says: "Hello".'},
        {"image": "nested/00001.png", "prompt": "Зелёный плащ, мягкий свет."},
    ]


def test_manifest_is_rebuilt_from_database_when_opening_legacy_project(tmp_path):
    project = Project.create(tmp_path / "legacy-project", "Legacy project")
    _add_captioned_image(project, "00001.png", "A legacy caption.")

    with connect(project.path) as connection:
        connection.execute(
            "DELETE FROM settings WHERE setting_key = ?",
            ("metadata_format",),
        )
        connection.commit()

    project.metadata_path.write_text("stale content\n", encoding="utf-8")
    reopened = Project.open(project.path)

    assert reopened.metadata_format == "jsonl"
    assert read_metadata_format(project.path) == "jsonl"
    assert [
        json.loads(line)
        for line in reopened.metadata_path.read_text(encoding="utf-8").splitlines()
    ] == [{"image": "00001.png", "prompt": "A legacy caption."}]


def test_manifest_does_not_export_rows_with_blank_captions(tmp_path):
    project = Project.create(tmp_path / "project", "Blank caption test")
    image_path = project.dataset_path / "00001.png"
    image_path.write_bytes(b"image")
    with connect(project.path) as connection:
        connection.execute(
            """
            INSERT INTO images (
                filename, original_filename, original_path,
                normalized_path, status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("source.png", "source.png", "/source/source.png", str(image_path), "Normalized"),
        )
        connection.commit()

    sync_training_metadata(project.path, project.dataset_path)
    assert project.metadata_path.read_text(encoding="utf-8") == ""


def test_manifest_rejects_normalized_image_paths_outside_dataset(tmp_path):
    project = Project.create(tmp_path / "project", "Path validation test")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"image")

    with connect(project.path) as connection:
        connection.execute(
            """
            INSERT INTO images (
                filename, original_filename, original_path,
                normalized_path, status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("outside.png", "outside.png", "/source/outside.png", str(outside), "Reviewed"),
        )
        image_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            "INSERT INTO captions (image_id, caption_text) VALUES (?, ?)",
            (image_id, "Caption."),
        )
        connection.commit()

    with pytest.raises(ValueError, match="outside the project dataset"):
        sync_training_metadata(project.path, project.dataset_path)
