"""Background batch worker for image caption generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from universal_dataset_builder.dataset.caption_files import write_caption_sidecar
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
    sidecar_warnings: tuple[str, ...]


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


def _resolve_image_path(
    row: dict[str, object],
    source_directory: Path,
    dataset_directory: Path,
) -> Path:
    """Resolve a source/normalized path and reject references outside the project."""
    normalized = row.get("normalized_path")
    candidates = []
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


class CaptionWorkerSignals(QObject):
    """Signals emitted by a batch caption task."""

    progress = Signal(int, int, str)
    completed = Signal(object)
    failed = Signal(str)


class CaptionWorker(QRunnable):
    """Generate and store captions sequentially without blocking the GUI."""

    def __init__(
        self,
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
    ) -> None:
        super().__init__()
        self.database_path = Path(database_path)
        self.source_directory = Path(source_directory)
        self.dataset_directory = Path(dataset_directory)
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.prompt = prompt
        self.selection_mode = selection_mode
        self.limit = limit
        self._cancel_event = Event()
        self.signals = CaptionWorkerSignals()

    def cancel(self) -> None:
        """Request cancellation between images."""
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            rows = read_images(self.database_path)
            targets = select_caption_targets(rows, self.selection_mode, self.limit)
            generated = 0
            failed = 0
            cancelled = False
            failed_files: list[str] = []
            sidecar_warnings: list[str] = []

            with OpenAICompatibleClient(
                self.base_url,
                api_key=self.api_key,
                timeout_seconds=self.timeout_seconds,
            ) as client:
                for index, row in enumerate(targets, start=1):
                    filename = str(row["filename"])
                    if self._cancel_event.is_set():
                        cancelled = True
                        break

                    self.signals.progress.emit(index - 1, len(targets), filename)
                    try:
                        image_path = _resolve_image_path(
                            row,
                            self.source_directory,
                            self.dataset_directory,
                        )
                        caption = client.caption_image(image_path, self.prompt, self.model)
                        normalized_path = save_generated_caption(
                            self.database_path,
                            int(row["image_id"]),
                            caption,
                            model_name=self.model,
                            prompt_template=self.prompt,
                        )
                        if normalized_path:
                            try:
                                write_caption_sidecar(
                                    self.dataset_directory,
                                    Path(normalized_path),
                                    caption,
                                )
                            except (OSError, ValueError) as error:
                                sidecar_warnings.append(f"{filename}: {error}")
                        generated += 1
                    except Exception as error:
                        LOGGER.exception("Caption generation failed for %s", filename)
                        failed += 1
                        failed_files.append(f"{filename}: {error}")
                    finally:
                        self.signals.progress.emit(index, len(targets), filename)

            self.signals.completed.emit(
                CaptionSummary(
                    discovered=len(targets),
                    generated=generated,
                    failed=failed,
                    cancelled=cancelled,
                    failed_files=tuple(failed_files),
                    sidecar_warnings=tuple(sidecar_warnings),
                )
            )
        except Exception as error:
            LOGGER.exception("Caption generation task failed")
            self.signals.failed.emit(str(error))
