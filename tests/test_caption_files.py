from __future__ import annotations

import pytest

from universal_dataset_builder.dataset.caption_files import (
    caption_sidecar_path,
    write_caption_sidecar,
)


def test_caption_sidecar_is_written_next_to_normalized_image(tmp_path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    image = dataset / "00001.png"
    image.write_bytes(b"image data")

    sidecar = write_caption_sidecar(dataset, image, "  A gray wolf.  ")

    assert sidecar == dataset / "00001.txt"
    assert sidecar.read_text(encoding="utf-8") == "A gray wolf.\n"


def test_caption_sidecar_rejects_paths_outside_dataset(tmp_path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"image data")

    with pytest.raises(ValueError, match="inside the project dataset"):
        caption_sidecar_path(dataset, outside)


def test_caption_sidecar_requires_existing_image_and_nonempty_caption(tmp_path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()

    with pytest.raises(FileNotFoundError):
        write_caption_sidecar(dataset, dataset / "missing.png", "Caption")

    image = dataset / "00001.png"
    image.write_bytes(b"image data")
    with pytest.raises(ValueError, match="cannot be empty"):
        write_caption_sidecar(dataset, image, "   ")
