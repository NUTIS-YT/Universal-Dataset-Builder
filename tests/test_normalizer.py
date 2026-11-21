from __future__ import annotations

import hashlib
import shutil

from PIL import Image

from universal_dataset_builder.core.project import Project
from universal_dataset_builder.dataset.normalizer import normalize_project_images
from universal_dataset_builder.storage.database import connect, read_images


def _index_image(project, _image_path):
    from universal_dataset_builder.dataset.scanner import scan_directory

    scan_directory(project.path, project.source_path)


def test_normalizer_creates_numbered_png_without_modifying_source(tmp_path):
    project = Project.create(tmp_path / "project", "Normalize test")
    source = project.source_path / "wolf.jpg"
    Image.new("RGB", (32, 18), "navy").save(source, quality=90)
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    _index_image(project, source)

    summary = normalize_project_images(
        project.path,
        project.source_path,
        project.dataset_path,
    )

    output = project.dataset_path / "00001.png"
    assert summary.normalized == 1
    assert summary.failed == 0
    assert output.is_file()
    with Image.open(output) as normalized:
        assert normalized.format == "PNG"
        assert normalized.size == (32, 18)
        assert normalized.mode == "RGB"
        assert normalized.info.get("icc_profile")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    assert read_images(project.path)[0]["normalized_path"] == str(output)


def test_normalizer_applies_exif_orientation(tmp_path):
    project = Project.create(tmp_path / "project", "EXIF test")
    source = project.source_path / "rotated.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (20, 10), "orange").save(source, exif=exif)
    _index_image(project, source)

    summary = normalize_project_images(
        project.path, project.source_path, project.dataset_path
    )

    with Image.open(project.dataset_path / "00001.png") as output:
        assert output.size == (10, 20)
    assert summary.normalized == 1


def test_normalizer_preserves_or_flattens_transparency(tmp_path):
    project = Project.create(tmp_path / "project", "Alpha test")
    source = project.source_path / "transparent.png"
    image = Image.new("RGBA", (12, 8), (255, 0, 0, 0))
    image.putpixel((0, 0), (255, 0, 0, 128))
    image.save(source)
    _index_image(project, source)

    preserved = normalize_project_images(
        project.path, project.source_path, project.dataset_path, alpha_mode="preserve"
    )
    with Image.open(project.dataset_path / "00001.png") as output:
        assert output.mode == "RGBA"
        assert output.getpixel((0, 0))[3] == 128
        assert output.getpixel((1, 1))[3] == 0
    assert preserved.normalized == 1

    # A second project checks flattening independently.
    flat_project = Project.create(tmp_path / "flat-project", "Flatten test")
    shutil.copy2(source, flat_project.source_path / source.name)
    _index_image(flat_project, source)
    result = normalize_project_images(
        flat_project.path,
        flat_project.source_path,
        flat_project.dataset_path,
        alpha_mode="white",
    )
    with Image.open(flat_project.dataset_path / "00001.png") as output:
        assert output.mode == "RGB"
        assert output.getpixel((1, 1)) == (255, 255, 255)
    assert result.normalized == 1


def test_normalizer_skips_exact_visual_duplicates(tmp_path):
    project = Project.create(tmp_path / "project", "Duplicate test")
    Image.new("RGB", (10, 10), "green").save(project.source_path / "a.png")
    shutil.copy2(project.source_path / "a.png", project.source_path / "b.png")
    _index_image(project, project.source_path / "a.png")

    summary = normalize_project_images(
        project.path, project.source_path, project.dataset_path
    )

    assert summary.normalized == 1
    assert summary.duplicates == 1
    assert sorted(path.name for path in project.dataset_path.glob("*.png")) == [
        "00001.png"
    ]


def test_normalizer_resumes_and_never_overwrites_existing_files(tmp_path):
    project = Project.create(tmp_path / "project", "Resume test")
    Image.new("RGB", (9, 9), "blue").save(project.source_path / "a.png")
    _index_image(project, project.source_path / "a.png")

    first = normalize_project_images(
        project.path, project.source_path, project.dataset_path
    )
    second = normalize_project_images(
        project.path, project.source_path, project.dataset_path
    )
    assert first.normalized == 1
    assert second.already_normalized == 1
    assert second.normalized == 0

    collision_project = Project.create(tmp_path / "collision-project", "Collision test")
    Image.new("RGB", (9, 9), "yellow").save(collision_project.source_path / "a.png")
    _index_image(collision_project, collision_project.source_path / "a.png")
    sentinel = collision_project.dataset_path / "00001.png"
    sentinel.write_bytes(b"do not overwrite")

    collision = normalize_project_images(
        collision_project.path,
        collision_project.source_path,
        collision_project.dataset_path,
    )
    assert collision.normalized == 1
    assert collision.conflicts == 1
    assert sentinel.read_bytes() == b"do not overwrite"
    assert (collision_project.dataset_path / "00002.png").is_file()


def test_normalizer_copies_existing_captions_and_keeps_reviewed_status(tmp_path):
    project = Project.create(tmp_path / "project", "Caption sidecar test")
    Image.new("RGB", (10, 10), "purple").save(project.source_path / "a.png")
    _index_image(project, project.source_path / "a.png")
    with connect(project.path) as connection:
        image_id = connection.execute("SELECT image_id FROM images").fetchone()["image_id"]
        connection.execute(
            """
            INSERT INTO captions (image_id, caption_text, reviewed)
            VALUES (?, ?, 1)
            """,
            (image_id, "A purple square."),
        )
        connection.commit()

    summary = normalize_project_images(
        project.path, project.source_path, project.dataset_path
    )

    assert summary.normalized == 1
    assert (project.dataset_path / "00001.txt").read_text(encoding="utf-8") == (
        "A purple square.\n"
    )
    assert read_images(project.path)[0]["status"] == "Reviewed"


def test_normalizer_ignores_failed_and_excluded_records(tmp_path):
    project = Project.create(tmp_path / "project", "Skip status test")
    Image.new("RGB", (4, 4), "red").save(project.source_path / "skip.png")
    _index_image(project, project.source_path / "skip.png")
    with connect(project.path) as connection:
        connection.execute("UPDATE images SET status = 'Excluded'")
        connection.commit()

    summary = normalize_project_images(
        project.path, project.source_path, project.dataset_path
    )
    assert summary.discovered == 0
    assert summary.normalized == 0


def test_invalid_icc_profile_is_reported_without_output(tmp_path):
    project = Project.create(tmp_path / "project", "Invalid ICC test")
    source = project.source_path / "bad-profile.png"
    Image.new("RGB", (8, 8), "red").save(source, icc_profile=b"not-an-icc-profile")
    _index_image(project, source)

    summary = normalize_project_images(
        project.path, project.source_path, project.dataset_path
    )
    assert summary.failed == 1
    assert summary.normalized == 0
    assert not (project.dataset_path / "00001.png").exists()



def test_normalizer_requires_rescan_when_source_changed(tmp_path):
    project = Project.create(tmp_path / "project", "Changed source test")
    source = project.source_path / "source.png"
    Image.new("RGB", (10, 10), "red").save(source)
    _index_image(project, source)
    Image.new("RGB", (10, 10), "blue").save(source)

    summary = normalize_project_images(
        project.path, project.source_path, project.dataset_path
    )

    assert summary.failed == 1
    assert "Run Scan source first" in summary.failed_files[0]
    assert not (project.dataset_path / "00001.png").exists()


def test_normalizer_sorts_and_uses_custom_start_number(tmp_path):
    project = Project.create(tmp_path / "project", "Sorting test")
    Image.new("RGB", (5, 5), "red").save(project.source_path / "zebra.png")
    Image.new("RGB", (5, 5), "blue").save(project.source_path / "ant.png")
    _index_image(project, project.source_path / "zebra.png")

    summary = normalize_project_images(
        project.path,
        project.source_path,
        project.dataset_path,
        start_number=42,
        sort_mode="filename_asc",
    )

    rows = read_images(project.path)
    paths_by_source = {row["filename"]: Path(row["normalized_path"]).name for row in rows}
    assert paths_by_source == {"ant.png": "00042.png", "zebra.png": "00043.png"}
    assert summary.normalized == 2


def test_normalizer_can_be_cancelled_between_images(tmp_path):
    project = Project.create(tmp_path / "project", "Cancellation test")
    Image.new("RGB", (5, 5), "red").save(project.source_path / "a.png")
    Image.new("RGB", (5, 5), "blue").save(project.source_path / "b.png")
    _index_image(project, project.source_path / "a.png")
    cancel = [False]

    def progress(current, total, filename):
        if current >= 1:
            cancel[0] = True

    summary = normalize_project_images(
        project.path,
        project.source_path,
        project.dataset_path,
        progress_callback=progress,
        cancel_requested=lambda: cancel[0],
    )

    assert summary.cancelled
    assert summary.normalized == 1
    assert len(list(project.dataset_path.glob("*.png"))) == 1
