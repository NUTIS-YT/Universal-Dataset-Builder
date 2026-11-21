"""Project lifecycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from universal_dataset_builder.storage.database import (
    create_project_database,
    read_project_metadata,
    read_project_statistics,
)


@dataclass(frozen=True, slots=True)
class Project:
    """An opened Universal Dataset Builder project."""

    path: Path
    name: str
    source_path: Path
    dataset_path: Path

    @classmethod
    def create(cls, directory: Path, name: str) -> Project:
        """Create a project in an existing or newly-created directory."""
        clean_name = name.strip()
        if not clean_name or clean_name in {".", ".."}:
            raise ValueError("Project name cannot be empty or a path component.")

        root = Path(directory).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        database_path = root / "project.fdb"
        if database_path.exists():
            raise FileExistsError(f"A project already exists at {database_path}")

        source_path = root / "source"
        dataset_path = root / "dataset"
        source_path.mkdir(exist_ok=True)
        dataset_path.mkdir(exist_ok=True)

        try:
            create_project_database(database_path, clean_name, str(dataset_path))
        except Exception:
            database_path.unlink(missing_ok=True)
            raise

        return cls(
            path=database_path,
            name=clean_name,
            source_path=source_path,
            dataset_path=dataset_path,
        )

    @classmethod
    def open(cls, path: Path) -> Project:
        """Open an existing project database and validate its application ID."""
        database_path = Path(path).expanduser().resolve()
        metadata = read_project_metadata(database_path)
        root = database_path.parent
        source_path = root / "source"
        dataset_path = Path(metadata["dataset_path"])
        source_path.mkdir(exist_ok=True)
        dataset_path.mkdir(parents=True, exist_ok=True)
        return cls(
            path=database_path,
            name=metadata["project_name"],
            source_path=source_path,
            dataset_path=dataset_path,
        )

    def statistics(self) -> dict[str, int]:
        """Return the dashboard counters for this project."""
        return read_project_statistics(self.path)
