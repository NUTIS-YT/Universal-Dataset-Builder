"""Safe text sidecar handling for normalized dataset images."""

from __future__ import annotations

from pathlib import Path


def caption_sidecar_path(dataset_directory: Path, normalized_image: Path) -> Path:
    """Resolve a caption path while preventing writes outside the dataset folder."""
    dataset_root = Path(dataset_directory).expanduser().resolve()
    image_path = Path(normalized_image).expanduser().resolve()
    try:
        relative_path = image_path.relative_to(dataset_root)
    except ValueError as error:
        raise ValueError("Normalized images must be stored inside the project dataset folder.") from error

    if relative_path == Path("."):
        raise ValueError("A dataset directory cannot be used as an image path.")
    return (dataset_root / relative_path).with_suffix(".txt")


def write_caption_sidecar(
    dataset_directory: Path,
    normalized_image: Path,
    caption_text: str,
) -> Path:
    """Atomically write a UTF-8 caption next to an existing normalized image."""
    clean_caption = caption_text.strip()
    if not clean_caption:
        raise ValueError("Caption cannot be empty.")

    image_path = Path(normalized_image).expanduser().resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Normalized image does not exist: {image_path}")

    sidecar = caption_sidecar_path(dataset_directory, image_path)
    temporary = sidecar.with_name(f".{sidecar.name}.tmp")
    try:
        temporary.write_text(f"{clean_caption}\n", encoding="utf-8")
        temporary.replace(sidecar)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return sidecar
