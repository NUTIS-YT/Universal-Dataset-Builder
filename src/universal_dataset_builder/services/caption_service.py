"""VLM caption-generation workflow independent of Qt workers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from universal_dataset_builder.dataset.metadata import sync_training_metadata
from universal_dataset_builder.storage.database import (
    read_images,
    save_generated_caption,
)
from universal_dataset_builder.vlm.client import OpenAICompatibleClient

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CaptionSummary:
    """Counts and diagnostics from one caption generation run."""

    discovered: int
    generated: int
    failed: int
    cancelled: bool
    failed_files: tuple[str, ...]
    metadata_warning: str | None = None


def select_caption_targets(
    images: list[dict[str, object]],
    mode: str,
    limit: int = 0,
) -> list[dict[str, object]]:
    """Select eligible records; zero limit means all matching images."""
    if mode == "missing":
        selected = [
            row for row in images
            if row["status"] not in {"Failed", "Excluded"}
            and not str(row.get("caption_text") or "").strip()
        ]
    elif mode == "unreviewed":
        selected = [
            row for row in images
            if row["status"] in {"Pending", "Normalized", "Captioned"}
            and not bool(row.get("caption_reviewed"))
        ]
    else:
        raise ValueError(f"Unsupported caption generation mode: {mode}")

    selected.sort(key=lambda row: str(row["filename"]).casefold())
    return selected[:limit] if limit > 0 else selected


def resolve_image_path(
    row: dict[str, object],
    source_directory: Path,
    dataset_directory: Path,
) -> Path:
    """Resolve an image path and reject references outside the project."""
    normalized = row.get("normalized_path")
    candidates: list[tuple[Path, Path]] = []
    if normalized:
        candidates.append((Path(str(normalized)), dataset_directory))
    candidates.append((Path(str(row["original_path"])), source_directory))

    for candidate, root in candidates:
        resolved = candidate.expanduser().resolve()
        resolved_root = root.expanduser().resolve()
        try:
            resolved.relative_to(resolved_root)
        except ValueError as error:
            raise ValueError("Image path points outside its project folder.") from error
        if resolved.is_file():
            return resolved

    raise FileNotFoundError(f"Image file is missing: {row['filename']}")


class CaptionGenerationService:
    """Generate, persist, and export captions without requiring a GUI event loop."""

    @staticmethod
    def generate(
        database_path: Path,
        source_directory: Path,
        dataset_directory: Path,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
        model: str,
        prompt: str,
        selection_mode: str,
        limit: int,
        cancel_requested: Callable[[], bool] | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> CaptionSummary:
        """Generate captions sequentially and report progress through a callback.

        Cancellation is checked between image requests. A failure for one image is
        recorded in the summary and does not prevent later images from processing.
        """
        database = Path(database_path)
        source_root = Path(source_directory)
        dataset_root = Path(dataset_directory)
        rows = read_images(database)
        targets = select_caption_targets(rows, selection_mode, limit)
        generated = 0
        failed = 0
        cancelled = False
        failed_files: list[str] = []
        metadata_warning: str | None = None

        with OpenAICompatibleClient(
            base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        ) as client:
            for index, row in enumerate(targets, start=1):
                filename = str(row["filename"])
                if cancel_requested is not None and cancel_requested():
                    cancelled = True
                    break

                if progress_callback is not None:
                    progress_callback(index - 1, len(targets), filename)

                try:
                    image_path = resolve_image_path(row, source_root, dataset_root)
                    caption = client.caption_image(image_path, prompt, model)
                    save_generated_caption(
                        database,
                        int(row["image_id"]),
                        caption,
                        model_name=model,
                        prompt_template=prompt,
                    )
                    generated += 1
                except Exception as error:
                    LOGGER.exception("Caption generation failed for %s", filename)
                    failed += 1
                    failed_files.append(f"{filename}: {error}")
                finally:
                    if progress_callback is not None:
                        progress_callback(index, len(targets), filename)

        if generated:
            try:
                sync_training_metadata(database, dataset_root)
            except Exception as error:
                LOGGER.exception("Could not update JSONL training metadata")
                metadata_warning = str(error)

        return CaptionSummary(
            discovered=len(targets),
            generated=generated,
            failed=failed,
            cancelled=cancelled,
            failed_files=tuple(failed_files),
            metadata_warning=metadata_warning,
        )
