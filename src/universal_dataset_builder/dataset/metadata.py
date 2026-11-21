"""Project-level training metadata stored as a single JSON Lines manifest."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from universal_dataset_builder.storage.database import (
    connect,
    read_images,
    read_project_metadata,
)

JSONL_METADATA_FORMAT = "jsonl"
SUPPORTED_METADATA_FORMATS = (JSONL_METADATA_FORMAT,)
_METADATA_FILENAMES = {JSONL_METADATA_FORMAT: "metadata.jsonl"}


def read_metadata_format(database_path: Path) -> str:
    """Read the project's metadata format, defaulting legacy projects to JSONL."""
    read_project_metadata(database_path)
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT setting_value FROM settings WHERE setting_key = ?",
            ("metadata_format",),
        ).fetchone()

    metadata_format = str(row["setting_value"]) if row is not None else JSONL_METADATA_FORMAT
    if metadata_format not in SUPPORTED_METADATA_FORMATS:
        raise ValueError(f"Unsupported project metadata format: {metadata_format}")
    return metadata_format


def sync_training_metadata(
    database_path: Path,
    dataset_directory: Path,
) -> Path:
    """Atomically rebuild the trainer-compatible manifest from project captions.

    Paths in the manifest are relative to dataset/. Only existing normalized
    images with non-empty captions are exported. The SQLite project database
    remains the source of truth for application state and caption review data.
    """
    database = Path(database_path).expanduser().resolve()
    dataset_root = Path(dataset_directory).expanduser().resolve()
    project_metadata = read_project_metadata(database)
    recorded_root = Path(project_metadata["dataset_path"]).expanduser().resolve()
    if dataset_root != recorded_root:
        raise ValueError("The output directory does not match this project's dataset/ folder.")

    metadata_format = read_metadata_format(database)
    filename = _METADATA_FILENAMES[metadata_format]
    dataset_root.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, str]] = []
    for row in read_images(database):
        if row["status"] in {"Failed", "Excluded"}:
            continue

        caption = str(row.get("caption_text") or "").strip()
        normalized_path_value = row.get("normalized_path")
        if not caption or not normalized_path_value:
            continue

        image_path = Path(str(normalized_path_value)).expanduser().resolve()
        try:
            relative_path = image_path.relative_to(dataset_root)
        except ValueError as error:
            raise ValueError(
                f"Normalized image is outside the project dataset folder: {image_path}"
            ) from error

        if relative_path == Path("."):
            raise ValueError("The dataset directory cannot be used as an image path.")
        if not image_path.is_file():
            continue

        records.append(
            {
                "image": relative_path.as_posix(),
                "prompt": caption,
            }
        )

    records.sort(key=lambda item: (item["image"].casefold(), item["image"]))
    manifest_path = dataset_root / filename
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{filename}.",
        suffix=".tmp",
        dir=dataset_root,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False))
                stream.write("\n")
        temporary_path.replace(manifest_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return manifest_path
