"""SQLite schema and persistence primitives for project files."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

APPLICATION_ID = 0x55444231  # UDB1
SCHEMA_VERSION = 1
IMAGE_STATUSES = ("Pending", "Normalized", "Captioned", "Reviewed", "Failed", "Excluded")


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
    return datetime.now(UTC).isoformat(timespec="seconds")


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
            CHECK (
                status IN (
                    'Pending', 'Normalized', 'Captioned',
                    'Reviewed', 'Failed', 'Excluded'
                )
            )
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


def read_images(database_path: Path) -> list[dict[str, object]]:
    """Return indexed images together with their latest caption, if one exists."""
    read_project_metadata(database_path)
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                images.image_id,
                images.filename,
                images.original_filename,
                images.original_path,
                images.normalized_path,
                images.width,
                images.height,
                images.format,
                images.file_hash,
                images.status,
                COALESCE((
                    SELECT captions.caption_text
                    FROM captions
                    WHERE captions.image_id = images.image_id
                    ORDER BY captions.caption_id DESC
                    LIMIT 1
                ), '') AS caption_text,
                COALESCE((
                    SELECT captions.reviewed
                    FROM captions
                    WHERE captions.image_id = images.image_id
                    ORDER BY captions.caption_id DESC
                    LIMIT 1
                ), 0) AS caption_reviewed
            FROM images
            ORDER BY images.filename COLLATE NOCASE, images.filename
            """
        ).fetchall()
    return [dict(row) for row in rows]


def save_image_caption(database_path: Path, image_id: int, caption_text: str) -> str | None:
    """Save one reviewed caption and return the normalized image path, if present."""
    clean_caption = caption_text.strip()
    if not clean_caption:
        raise ValueError("Caption cannot be empty.")

    with connect(database_path) as connection:
        image = connection.execute(
            "SELECT normalized_path FROM images WHERE image_id = ?",
            (image_id,),
        ).fetchone()
        if image is None:
            raise ValueError(f"Image record {image_id} does not exist.")

        connection.execute("DELETE FROM captions WHERE image_id = ?", (image_id,))
        now = _timestamp()
        connection.execute(
            """
            INSERT INTO captions (image_id, caption_text, generated_at, reviewed)
            VALUES (?, ?, ?, 1)
            """,
            (image_id, clean_caption, now),
        )
        connection.execute(
            "UPDATE images SET status = 'Reviewed' WHERE image_id = ?",
            (image_id,),
        )
        connection.execute(
            "UPDATE projects SET updated_at = ? WHERE project_id = 1",
            (now,),
        )
        connection.commit()

    normalized_path = image["normalized_path"]
    return str(normalized_path) if normalized_path else None


def set_image_status(database_path: Path, image_id: int, status: str) -> None:
    """Update an image status while enforcing caption prerequisites."""
    if status not in IMAGE_STATUSES:
        raise ValueError(f"Unsupported image status: {status}")

    with connect(database_path) as connection:
        image = connection.execute(
            "SELECT image_id FROM images WHERE image_id = ?",
            (image_id,),
        ).fetchone()
        if image is None:
            raise ValueError(f"Image record {image_id} does not exist.")

        caption = connection.execute(
            """
            SELECT 1 FROM captions
            WHERE image_id = ? AND TRIM(caption_text) <> ''
            LIMIT 1
            """,
            (image_id,),
        ).fetchone()
        if status in {"Captioned", "Reviewed"} and caption is None:
            raise ValueError(f"An image needs a caption before it can be marked {status}.")

        now = _timestamp()
        connection.execute(
            "UPDATE images SET status = ? WHERE image_id = ?",
            (status, image_id),
        )
        connection.execute(
            "UPDATE captions SET reviewed = ? WHERE image_id = ?",
            (1 if status == "Reviewed" else 0, image_id),
        )
        connection.execute(
            "UPDATE projects SET updated_at = ? WHERE project_id = 1",
            (now,),
        )
        connection.commit()
