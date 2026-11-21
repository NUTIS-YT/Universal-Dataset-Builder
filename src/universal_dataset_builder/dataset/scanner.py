"""Scan source folders and index supported images in a project database."""

from __future__ import annotations

import hashlib
import warnings
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from universal_dataset_builder.dataset.metadata import sync_training_metadata
from universal_dataset_builder.storage.database import connect, read_project_metadata

SUPPORTED_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
)
_PROGRESS_BATCH_SIZE = 50


@dataclass(frozen=True, slots=True)
class ScanSummary:
    """Counts produced by one scan operation."""

    discovered: int
    added: int
    updated: int
    unchanged: int
    failed: int
    failed_files: tuple[str, ...]
    metadata_warning: str | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inspect_image(
    path: Path,
) -> tuple[int | None, int | None, str, str | None, str | None]:
    """Return dimensions, format, hash and a validation error, if any."""
    image_hash: str | None
    hash_error: str | None = None
    try:
        image_hash = _sha256(path)
    except OSError as error:
        image_hash = None
        hash_error = str(error)

    width: int | None = None
    height: int | None = None
    image_format = path.suffix.lstrip(".").upper() or "UNKNOWN"
    validation_error = hash_error

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                image_format = image.format or image_format
                width, height = image.size
                orientation = image.getexif().get(274, 1)
                if orientation in {5, 6, 7, 8}:
                    width, height = height, width

            # Pillow requires verify() to be called immediately after open().
            with Image.open(path) as verification_image:
                verification_image.verify()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as error:
        width = None
        height = None
        validation_error = str(error) or error.__class__.__name__

    return width, height, image_format, image_hash, validation_error


def _iter_image_files(source: Path, recursive: bool) -> list[Path]:
    candidates: Iterable[Path] = source.rglob("*") if recursive else source.iterdir()
    files: list[Path] = []
    for candidate in candidates:
        try:
            if candidate.is_symlink() or not candidate.is_file():
                continue
            if candidate.suffix.casefold() in SUPPORTED_EXTENSIONS:
                files.append(candidate)
        except OSError:
            continue

    def sort_key(item: Path) -> tuple[str, str]:
        relative_name = item.relative_to(source).as_posix()
        return relative_name.casefold(), relative_name

    return sorted(files, key=sort_key)


def scan_directory(
    database_path: Path,
    source_directory: Path,
    *,
    recursive: bool = True,
    progress_callback: Callable[[int, int], None] | None = None,
) -> ScanSummary:
    """Scan a directory without modifying source files and index images in SQLite.

    The source-relative path is used as the unique image filename, so equal
    basenames in different subdirectories remain distinct. After the database
    is updated, the trainer metadata manifest is rebuilt to remove stale pairs.
    """
    database_path = Path(database_path).expanduser().resolve()
    source = Path(source_directory).expanduser().resolve()
    project_metadata = read_project_metadata(database_path)
    if not source.is_dir():
        raise NotADirectoryError(f"Source directory does not exist: {source}")

    files = _iter_image_files(source, recursive)
    added = 0
    updated = 0
    unchanged = 0
    failed = 0
    failed_files: list[str] = []

    with connect(database_path) as connection:
        for index, path in enumerate(files, start=1):
            relative_name = path.relative_to(source).as_posix()
            width, height, image_format, image_hash, validation_error = _inspect_image(path)
            status = "Failed" if validation_error else "Pending"
            if status == "Failed":
                failed += 1
                failed_files.append(relative_name)

            existing = connection.execute(
                "SELECT image_id, file_hash FROM images WHERE filename = ?",
                (relative_name,),
            ).fetchone()

            if existing is None:
                connection.execute(
                    """
                    INSERT INTO images (
                        filename, original_filename, original_path,
                        width, height, format, file_hash, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        relative_name,
                        path.name,
                        str(path),
                        width,
                        height,
                        image_format,
                        image_hash,
                        status,
                    ),
                )
                added += 1
            elif image_hash is not None and existing["file_hash"] == image_hash:
                unchanged += 1
            else:
                connection.execute(
                    "DELETE FROM captions WHERE image_id = ?",
                    (existing["image_id"],),
                )
                connection.execute(
                    """
                    UPDATE images
                    SET original_filename = ?, original_path = ?,
                        normalized_path = NULL, width = ?, height = ?,
                        format = ?, file_hash = ?, status = ?
                    WHERE image_id = ?
                    """,
                    (
                        path.name,
                        str(path),
                        width,
                        height,
                        image_format,
                        image_hash,
                        status,
                        existing["image_id"],
                    ),
                )
                updated += 1

            if index % _PROGRESS_BATCH_SIZE == 0:
                connection.commit()
            if progress_callback is not None:
                progress_callback(index, len(files))

        connection.commit()

    metadata_warning: str | None = None
    try:
        sync_training_metadata(
            database_path,
            Path(project_metadata["dataset_path"]),
        )
    except Exception as error:
        metadata_warning = str(error)

    return ScanSummary(
        discovered=len(files),
        added=added,
        updated=updated,
        unchanged=unchanged,
        failed=failed,
        failed_files=tuple(failed_files),
        metadata_warning=metadata_warning,
    )
