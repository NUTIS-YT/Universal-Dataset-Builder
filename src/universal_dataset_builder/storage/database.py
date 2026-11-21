"""SQLite schema and persistence primitives for project files."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

APPLICATION_ID = 0x55444231  # UDB1
SCHEMA_VERSION = 1


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a configured SQLite connection and always close it."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_project_database(database_path: Path, name: str, dataset_path: str) -> None:
    """Create a new project database and its initial schema."""
    database_path = Path(database_path)
    if database_path.exists():
        raise FileExistsError(f"Project database already exists: {database_path}")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    now = _timestamp()
    schema = """
    CREATE TABLE projects (
        project_id INTEGER PRIMARY KEY CHECK (project_id = 1),
        project_name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        dataset_path TEXT NOT NULL
    );

    CREATE TABLE images (
        image_id INTEGER PRIMARY KEY,
        filename TEXT NOT NULL UNIQUE,
        original_filename TEXT NOT NULL,
        original_path TEXT NOT NULL,
        normalized_path TEXT,
        width INTEGER,
        height INTEGER,
        format TEXT,
        file_hash TEXT,
        status TEXT NOT NULL DEFAULT 'Pending'
            CHECK (status IN ('Pending', 'Normalized', 'Captioned', 'Reviewed', 'Failed', 'Excluded'))
    );

    CREATE TABLE captions (
        caption_id INTEGER PRIMARY KEY,
        image_id INTEGER NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
        caption_text TEXT NOT NULL DEFAULT '',
        prompt_template TEXT,
        model_name TEXT,
        generated_at TEXT,
        reviewed INTEGER NOT NULL DEFAULT 0 CHECK (reviewed IN (0, 1))
    );

    CREATE TABLE jobs (
        job_id INTEGER PRIMARY KEY,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL,
        total_items INTEGER NOT NULL DEFAULT 0,
        completed_items INTEGER NOT NULL DEFAULT 0,
        failed_items INTEGER NOT NULL DEFAULT 0,
        started_at TEXT,
        finished_at TEXT
    );

    CREATE TABLE models (
        model_id INTEGER PRIMARY KEY,
        api_url TEXT NOT NULL,
        model_name TEXT NOT NULL,
        profile_name TEXT
    );

    CREATE TABLE settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT NOT NULL
    );

    CREATE INDEX idx_images_status ON images(status);
    CREATE INDEX idx_captions_image_id ON captions(image_id);
    """
    with connect(database_path) as connection:
        connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.executescript(schema)
        connection.execute(
            """
            INSERT INTO projects (
                project_id, project_name, created_at, updated_at, dataset_path
            ) VALUES (1, ?, ?, ?, ?)
            """,
            (name, now, now, dataset_path),
        )
        connection.commit()


def read_project_metadata(database_path: Path) -> dict[str, str]:
    """Read project metadata after validating that the file is a UDB database."""
    database_path = Path(database_path)
    if not database_path.is_file():
        raise FileNotFoundError(f"Project file does not exist: {database_path}")

    try:
        with connect(database_path) as connection:
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            if application_id != APPLICATION_ID:
                raise ValueError("This file is not a Universal Dataset Builder project.")
            row = connection.execute(
                """
                SELECT project_name, dataset_path
                FROM projects
                WHERE project_id = 1
                """
            ).fetchone()
    except sqlite3.DatabaseError as error:
        raise ValueError(f"Cannot read project database: {error}") from error

    if row is None:
        raise ValueError("Project database is missing its project metadata.")
    return {
        "project_name": str(row["project_name"]),
        "dataset_path": str(row["dataset_path"]),
    }


def read_project_statistics(database_path: Path) -> dict[str, int]:
    """Read image and caption counters used by the dashboard."""
    read_project_metadata(database_path)
    with connect(database_path) as connection:
        images = connection.execute("SELECT COUNT(*) FROM images").fetchone()[0]
        captions = connection.execute("SELECT COUNT(*) FROM captions").fetchone()[0]
        reviewed = connection.execute(
            "SELECT COUNT(*) FROM images WHERE status = 'Reviewed'"
        ).fetchone()[0]
        failed = connection.execute(
            "SELECT COUNT(*) FROM images WHERE status = 'Failed'"
        ).fetchone()[0]
    return {
        "images": int(images),
        "captions": int(captions),
        "reviewed": int(reviewed),
        "failed": int(failed),
    }
