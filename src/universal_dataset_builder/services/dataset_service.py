"""Dataset workflows shared by the GUI and future API clients."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from universal_dataset_builder.dataset.metadata import sync_training_metadata
from universal_dataset_builder.dataset.normalizer import (
    NormalizationSummary,
    normalize_project_images,
)
from universal_dataset_builder.dataset.scanner import ScanSummary, scan_directory
from universal_dataset_builder.storage.database import (
    IMAGE_STATUSES,
    read_images,
    save_image_caption,
    set_image_status,
)


class DatasetService:
    """Run dataset operations without depending on a presentation framework."""

    statuses = IMAGE_STATUSES

    @staticmethod
    def list_images(database_path: Path) -> list[dict[str, object]]:
        """Return indexed images and their latest captions."""
        return read_images(Path(database_path))

    @staticmethod
    def scan_source(
        database_path: Path,
        source_directory: Path,
        *,
        recursive: bool = True,
        progress_callback: Callable[[int, int], None] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> ScanSummary:
        """Index source images and synchronize the training manifest."""
        return scan_directory(
            Path(database_path),
            Path(source_directory),
            recursive=recursive,
            progress_callback=progress_callback,
            cancel_requested=cancel_requested,
        )

    @staticmethod
    def normalize_images(
        database_path: Path,
        source_directory: Path,
        dataset_directory: Path,
        *,
        start_number: int = 1,
        alpha_mode: str = "preserve",
        skip_duplicates: bool = True,
        sort_mode: str = "filename_asc",
        progress_callback: Callable[[int, int, str], None] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> NormalizationSummary:
        """Normalize project images while preserving cancellation and progress hooks."""
        return normalize_project_images(
            Path(database_path),
            Path(source_directory),
            Path(dataset_directory),
            start_number=start_number,
            alpha_mode=alpha_mode,
            skip_duplicates=skip_duplicates,
            sort_mode=sort_mode,
            progress_callback=progress_callback,
            cancel_requested=cancel_requested,
        )

    @staticmethod
    def save_caption(
        database_path: Path,
        dataset_directory: Path,
        image_id: int,
        caption: str,
    ) -> str | None:
        """Save a reviewed caption and return any manifest synchronization warning.

        A database save remains successful even if rebuilding metadata.jsonl fails,
        matching the existing GUI's behavior and allowing the user to retry sync.
        """
        save_image_caption(Path(database_path), image_id, caption)
        try:
            sync_training_metadata(Path(database_path), Path(dataset_directory))
        except Exception as error:
            return str(error)
        return None

    @staticmethod
    def set_status(
        database_path: Path,
        dataset_directory: Path,
        image_id: int,
        status: str,
    ) -> str | None:
        """Change an image status and return any manifest synchronization warning."""
        set_image_status(Path(database_path), image_id, status)
        try:
            sync_training_metadata(Path(database_path), Path(dataset_directory))
        except Exception as error:
            return str(error)
        return None
