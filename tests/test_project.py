from __future__ import annotations

import pytest

from universal_dataset_builder.core.project import Project


def test_create_and_open_project(tmp_path):
    project_directory = tmp_path / "Sample Dataset"
    project = Project.create(project_directory, "Sample Dataset")

    assert project.path.name == "project.fdb"
    assert project.path.is_file()
    assert project.source_path.is_dir()
    assert project.dataset_path.is_dir()
    assert project.name == "Sample Dataset"
    assert project.metadata_format == "jsonl"
    assert project.metadata_path == project.dataset_path / "metadata.jsonl"
    assert project.metadata_path.is_file()
    assert project.metadata_path.read_text(encoding="utf-8") == ""

    reopened = Project.open(project.path)
    assert reopened.name == project.name
    assert reopened.path == project.path
    assert reopened.metadata_format == "jsonl"
    assert reopened.metadata_path.is_file()


def test_create_refuses_to_overwrite_existing_project(tmp_path):
    Project.create(tmp_path / "project", "First")
    with pytest.raises(FileExistsError):
        Project.create(tmp_path / "project", "Second")


def test_create_rejects_unsupported_metadata_format(tmp_path):
    with pytest.raises(ValueError, match="Unsupported metadata format"):
        Project.create(tmp_path / "project", "Bad format", metadata_format="csv")


def test_open_rejects_non_project_sqlite_file(tmp_path):
    wrong_file = tmp_path / "other.sqlite"
    wrong_file.write_text("not a database", encoding="utf-8")

    with pytest.raises(ValueError):
        Project.open(wrong_file)


def test_project_starts_with_zeroed_statistics(tmp_path):
    project = Project.create(tmp_path / "project", "Empty")
    assert project.statistics() == {
        "images": 0,
        "captions": 0,
        "reviewed": 0,
        "failed": 0,
    }
