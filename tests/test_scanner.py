from __future__ import annotations

import json

from PIL import Image

from universal_dataset_builder.core.project import Project
from universal_dataset_builder.dataset.normalizer import normalize_project_images
from universal_dataset_builder.dataset.scanner import scan_directory
from universal_dataset_builder.storage.database import connect, read_images


def test_scan_indexes_supported_images_and_reports_corrupt_files(tmp_path):
    project = Project.create(tmp_path / "project", "Scanner test")
    Image.new("RGB", (20, 12), "red").save(project.source_path / "wolf.png")
    nested = project.source_path / "animals"
    nested.mkdir()
    Image.new("RGB", (8, 8), "blue").save(nested / "fox.webp")
    (project.source_path / "broken.png").write_bytes(b"not an image")
    (project.source_path / "notes.txt").write_text("ignored", encoding="utf-8")

    summary = scan_directory(project.path, project.source_path)

    assert summary.discovered == 3
    assert summary.added == 3
    assert summary.failed == 1
    assert summary.failed_files == ("broken.png",)

    images = read_images(project.path)
    assert len(images) == 3
    by_name = {image["filename"]: image for image in images}
    assert by_name["wolf.png"]["width"] == 20
    assert by_name["wolf.png"]["height"] == 12
    assert by_name["animals/fox.webp"]["format"] == "WEBP"
    assert by_name["broken.png"]["status"] == "Failed"


def test_rescan_does_not_duplicate_unchanged_files(tmp_path):
    project = Project.create(tmp_path / "project", "Rescan test")
    image_path = project.source_path / "image.png"
    Image.new("RGB", (10, 10), "green").save(image_path)

    first = scan_directory(project.path, project.source_path)
    second = scan_directory(project.path, project.source_path)

    assert first.added == 1
    assert second.unchanged == 1
    assert second.added == 0
    assert len(read_images(project.path)) == 1


def test_changed_source_image_invalidates_caption_and_jsonl_pair(tmp_path):
    project = Project.create(tmp_path / "project", "Changed image test")
    image_path = project.source_path / "image.png"
    Image.new("RGB", (10, 10), "green").save(image_path)
    scan_directory(project.path, project.source_path)
    normalize_project_images(project.path, project.source_path, project.dataset_path)

    with connect(project.path) as connection:
        image_id = connection.execute(
            "SELECT image_id FROM images WHERE filename = 'image.png'"
        ).fetchone()["image_id"]
        connection.execute(
            """
            INSERT INTO captions (image_id, caption_text, reviewed)
            VALUES (?, ?, 1)
            """,
            (image_id, "old caption"),
        )
        connection.execute(
            "UPDATE images SET status = 'Reviewed' WHERE image_id = ?",
            (image_id,),
        )
        connection.commit()

    # Rebuild once to establish a previously valid training record.
    from universal_dataset_builder.dataset.metadata import sync_training_metadata

    sync_training_metadata(project.path, project.dataset_path)
    assert json.loads(project.metadata_path.read_text(encoding="utf-8")) == {
        "image": "00001.png",
        "prompt": "old caption",
    }

    Image.new("RGB", (18, 9), "purple").save(image_path)
    summary = scan_directory(project.path, project.source_path)

    assert summary.updated == 1
    assert summary.metadata_warning is None
    image = read_images(project.path)[0]
    assert image["width"] == 18
    assert image["height"] == 9
    assert image["status"] == "Pending"
    with connect(project.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM captions").fetchone()[0] == 0
    assert project.metadata_path.read_text(encoding="utf-8") == ""


def test_non_recursive_scan_only_indexes_top_level_files(tmp_path):
    project = Project.create(tmp_path / "project", "Non recursive test")
    Image.new("RGB", (4, 4), "red").save(project.source_path / "top.png")
    nested = project.source_path / "nested"
    nested.mkdir()
    Image.new("RGB", (4, 4), "blue").save(nested / "child.png")

    summary = scan_directory(project.path, project.source_path, recursive=False)

    assert summary.discovered == 1
    assert summary.added == 1
    assert [row["filename"] for row in read_images(project.path)] == ["top.png"]
