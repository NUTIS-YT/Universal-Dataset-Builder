from __future__ import annotations

import sqlite3

from universal_dataset_builder.core.project import Project
from universal_dataset_builder.storage.database import (
    APPLICATION_ID,
    SCHEMA_VERSION,
    connect,
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
