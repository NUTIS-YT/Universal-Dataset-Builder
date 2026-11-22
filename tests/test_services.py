from __future__ import annotations

from PIL import Image

from universal_dataset_builder.services.dataset_service import DatasetService
from universal_dataset_builder.services.project_service import ProjectService


def test_project_service_creates_opens_and_reports_statistics(tmp_path):
    project_path = tmp_path / "service-project"

    project = ProjectService.create(project_path, "Service project")
    reopened = ProjectService.open(project.path)

    assert reopened.name == "Service project"
    assert reopened.path == project.path
    assert ProjectService.statistics(reopened) == {
        "images": 0,
        "captions": 0,
        "reviewed": 0,
        "failed": 0,
    }


def test_dataset_service_scans_normalizes_and_lists_images(tmp_path):
    project = ProjectService.create(tmp_path / "dataset-project", "Dataset service")
    Image.new("RGB", (24, 16), "navy").save(project.source_path / "wolf.png")

    scan = DatasetService.scan_source(project.path, project.source_path)
    assert scan.discovered == 1
    assert scan.added == 1

    normalization = DatasetService.normalize_images(
        project.path,
        project.source_path,
        project.dataset_path,
    )
    assert normalization.normalized == 1
    assert normalization.failed == 0

    images = DatasetService.list_images(project.path)
    assert len(images) == 1
    assert images[0]["filename"] == "wolf.png"
    assert images[0]["status"] == "Normalized"
    assert images[0]["normalized_path"] is not None


def test_dataset_service_caption_and_status_sync_manifest(tmp_path):
    project = ProjectService.create(tmp_path / "caption-project", "Caption service")
    Image.new("RGB", (10, 10), "teal").save(project.source_path / "image.png")
    DatasetService.scan_source(project.path, project.source_path)
    DatasetService.normalize_images(
        project.path,
        project.source_path,
        project.dataset_path,
    )

    image = DatasetService.list_images(project.path)[0]
    warning = DatasetService.save_caption(
        project.path,
        project.dataset_path,
        int(image["image_id"]),
        "A teal square.",
    )

    assert warning is None
    assert DatasetService.list_images(project.path)[0]["status"] == "Reviewed"
    assert project.metadata_path.read_text(encoding="utf-8").strip() == (
        '{"image":"00001.png","prompt":"A teal square."}'
    )

    warning = DatasetService.set_status(
        project.path,
        project.dataset_path,
        int(image["image_id"]),
        "Excluded",
    )
    assert warning is None
    assert project.metadata_path.read_text(encoding="utf-8") == ""
