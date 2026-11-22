"""Project lifecycle services shared by desktop and API front ends."""

from __future__ import annotations

from pathlib import Path

from universal_dataset_builder.core.project import Project


class ProjectService:
    """Expose project lifecycle operations without UI dependencies."""

    @staticmethod
    def create(
        directory: Path,
        name: str,
        metadata_format: str = "jsonl",
    ) -> Project:
        """Create a project using the canonical project implementation."""
        return Project.create(directory, name, metadata_format=metadata_format)

    @staticmethod
    def open(database_path: Path) -> Project:
        """Open an existing project and rebuild its training manifest."""
        return Project.open(database_path)

    @staticmethod
    def statistics(project: Project) -> dict[str, int]:
        """Return dashboard statistics for an opened project."""
        return project.statistics()
