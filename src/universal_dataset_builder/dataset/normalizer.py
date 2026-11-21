"""Safe conversion of indexed source images into sequential PNG files."""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

from universal_dataset_builder.dataset.caption_files import write_caption_sidecar
from universal_dataset_builder.storage.database import (
    connect,
    read_images,
    read_project_metadata,
)


@dataclass(frozen=True, slots=True)
class NormalizationSummary:
    """Counts and diagnostic details from a normalization run."""

    discovered: int
    normalized: int
    already_normalized: int
    duplicates: int
    conflicts: int
    failed: int
    cancelled: bool
    failed_files: tuple[str, ...]


def _srgb_profile_bytes() -> bytes:
    """Return a stable embedded sRGB profile for every generated PNG."""
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    return profile.tobytes()


def _image_fingerprint(image: Image.Image) -> str:
    """Hash canonical output pixels to identify visual duplicates exactly."""
    digest = hashlib.sha256()
    digest.update(f"{image.mode}:{image.width}x{image.height}:".encode("ascii"))
    digest.update(image.tobytes())
    return digest.hexdigest()


def _prepare_image(
    source_path: Path,
    alpha_mode: str,
) -> tuple[Image.Image, str]:
    """Apply EXIF orientation, color-manage to sRGB and handle alpha."""
    if alpha_mode not in {"preserve", "white", "black"}:
        raise ValueError(f"Unsupported transparency mode: {alpha_mode}")

    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(source_path) as opened:
            image = ImageOps.exif_transpose(opened)
            has_alpha = "A" in image.getbands() or "transparency" in image.info
            alpha = None
            if has_alpha:
                rgba = image.convert("RGBA")
                alpha = rgba.getchannel("A")
                base = rgba.convert("RGB")
            else:
                base = image.convert("RGB")

            embedded_profile = image.info.get("icc_profile")
            if embedded_profile:
                input_profile = ImageCms.ImageCmsProfile(io.BytesIO(embedded_profile))
                output_profile = ImageCms.ImageCmsProfile(
                    ImageCms.createProfile("sRGB")
                )
                srgb = ImageCms.profileToProfile(
                    base,
                    input_profile,
                    output_profile,
                    outputMode="RGB",
                )
            else:
                # Images without an embedded profile are interpreted as sRGB.
                srgb = base

            if alpha is not None and alpha_mode == "preserve":
                result = srgb.convert("RGBA")
                result.putalpha(alpha)
            elif alpha is not None:
                background_color = (255, 255, 255) if alpha_mode == "white" else (0, 0, 0)
                background = Image.new("RGB", srgb.size, background_color)
                background.paste(srgb, mask=alpha)
                result = background
            else:
                result = srgb.convert("RGB")

    return result, _image_fingerprint(result)


def _safe_child_path(root: Path, candidate: Path) -> Path:
    """Resolve a path and ensure it stays inside the supplied project folder."""
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"Path is outside the project folder: {candidate}") from error
    return resolved_candidate


def _write_png_without_overwrite(
    image: Image.Image,
    destination: Path,
    icc_profile: bytes,
) -> None:
    """Write a PNG to a temporary file and atomically install it without clobbering."""
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)

    try:
        image.save(
            temporary_path,
            format="PNG",
            optimize=True,
            compress_level=6,
            icc_profile=icc_profile,
        )
        # A hard link is atomic and fails rather than replacing an existing file.
        os.link(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def _sort_images(
    images: list[dict[str, object]],
    sort_mode: str,
) -> list[dict[str, object]]:
    """Return indexed images in the selected deterministic order."""
    if sort_mode == "filename_desc":
        return sorted(
            images,
            key=lambda row: str(row["filename"]).casefold(),
            reverse=True,
        )
    if sort_mode == "largest_first":
        return sorted(
            images,
            key=lambda row: (
                -int(row["width"] or 0) * int(row["height"] or 0),
                str(row["filename"]).casefold(),
            ),
        )
    if sort_mode == "smallest_first":
        return sorted(
            images,
            key=lambda row: (
                int(row["width"] or 0) * int(row["height"] or 0),
                str(row["filename"]).casefold(),
            ),
        )
    if sort_mode == "filename_asc":
        return sorted(images, key=lambda row: str(row["filename"]).casefold())
    raise ValueError(f"Unsupported sorting mode: {sort_mode}")


def normalize_project_images(
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
    """Normalize indexed source images into PNGs without modifying originals.

    Existing files are never overwritten. A run can be resumed: records whose
    normalized output still exists are retained and skipped.
    """
    database = Path(database_path).expanduser().resolve()
    source_root = Path(source_directory).expanduser().resolve()
    dataset_root = Path(dataset_directory).expanduser().resolve()
    if start_number < 1:
        raise ValueError("Starting number must be at least 1.")
    if not source_root.is_dir():
        raise NotADirectoryError(f"Source directory does not exist: {source_root}")

    metadata = read_project_metadata(database)
    recorded_dataset = Path(metadata["dataset_path"]).expanduser().resolve()
    if recorded_dataset != dataset_root:
        raise ValueError("The output directory does not match this project's dataset/ folder.")
    if (
        source_root == dataset_root
        or source_root.is_relative_to(dataset_root)
        or dataset_root.is_relative_to(source_root)
    ):
        raise ValueError("Source and dataset directories must be separate, non-overlapping folders.")

    dataset_root.mkdir(parents=True, exist_ok=True)
    rows = _sort_images(read_images(database), sort_mode)
    eligible = [
        row for row in rows if row["status"] not in {"Failed", "Excluded"}
    ]

    normalized = 0
    already_normalized = 0
    duplicates = 0
    conflicts = 0
    failed = 0
    failed_files: list[str] = []
    cancelled = False
    next_number = start_number
    seen_fingerprints: set[str] = set()
    srgb_profile = _srgb_profile_bytes()

    for index, row in enumerate(eligible, start=1):
        relative_name = str(row["filename"])
        if cancel_requested is not None and cancel_requested():
            cancelled = True
            break

        if progress_callback is not None:
            progress_callback(index - 1, len(eligible), relative_name)

        try:
            source_path = _safe_child_path(source_root, Path(str(row["original_path"])))
            if not source_path.is_file():
                raise FileNotFoundError(f"Source image is missing: {source_path}")

            image, fingerprint = _prepare_image(source_path, alpha_mode)
            if fingerprint in seen_fingerprints and skip_duplicates:
                duplicates += 1
                continue
            seen_fingerprints.add(fingerprint)

            existing_normalized = row.get("normalized_path")
            if existing_normalized:
                normalized_path = _safe_child_path(
                    dataset_root,
                    Path(str(existing_normalized)),
                )
                if normalized_path.is_file():
                    caption = str(row.get("caption_text") or "")
                    if caption:
                        write_caption_sidecar(dataset_root, normalized_path, caption)
                    already_normalized += 1
                    continue

            while True:
                filename = f"{next_number:05d}.png"
                destination = dataset_root / filename
                next_number += 1
                if not destination.exists():
                    break
                conflicts += 1

            _write_png_without_overwrite(image, destination, srgb_profile)
            caption = str(row.get("caption_text") or "")
            sidecar: Path | None = None
            try:
                if caption:
                    sidecar = write_caption_sidecar(dataset_root, destination, caption)

                if caption and bool(row.get("caption_reviewed")):
                    new_status = "Reviewed"
                elif caption:
                    new_status = "Captioned"
                else:
                    new_status = "Normalized"

                with connect(database) as connection:
                    connection.execute(
                        """
                        UPDATE images
                        SET normalized_path = ?, status = ?
                        WHERE image_id = ?
                        """,
                        (str(destination), new_status, int(row["image_id"])),
                    )
                    connection.commit()
            except Exception:
                destination.unlink(missing_ok=True)
                if sidecar is not None:
                    sidecar.unlink(missing_ok=True)
                raise

            normalized += 1
        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            ImageCms.PyCMSError,
            UnidentifiedImageError,
            OSError,
            ValueError,
            SyntaxError,
        ) as error:
            failed += 1
            failed_files.append(f"{relative_name}: {error}")
        finally:
            if "image" in locals():
                image.close()
                del image

        if progress_callback is not None:
            progress_callback(index, len(eligible), relative_name)

    if progress_callback is not None:
        progress_callback(
            min(index if eligible else 0, len(eligible)),
            len(eligible),
            "Cancelled" if cancelled else "Complete",
        )

    return NormalizationSummary(
        discovered=len(eligible),
        normalized=normalized,
        already_normalized=already_normalized,
        duplicates=duplicates,
        conflicts=conflicts,
        failed=failed,
        cancelled=cancelled,
        failed_files=tuple(failed_files),
    )
