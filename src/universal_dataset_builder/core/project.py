"""Project lifecycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from universal_dataset_builder.dataset.metadata import (
    JSONL_METADATA_FORMAT,
    SUPPORTED_METADATA_FORMATS,
    read_metadata_format,
    sync_training_metadata,
)
from universal_dataset_builder.storage.database import (
    connect,
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
    metadata_format: str = JSONL_METADATA_FORMAT

    @property
    def metadata_path(self) -> Path:
        """Return the project's training metadata manifest."""
        return self.dataset_path / "metadata.jsonl"

    @classmethod
    def create(
        cls,
        directory: Path,
        name: str,
        metadata_format: str = JSONL_METADATA_FORMAT,
    ) -> Project:
        """Create a project and initialize its selected training metadata format."""
        clean_name = name.strip()
        if not clean_name or clean_name in {".", ".."}:
            raise ValueError("Project name cannot be empty or a path component.")
        if metadata_format not in SUPPORTED_METADATA_FORMATS:
            supported = ", ".join(SUPPORTED_METADATA_FORMATS)
            raise ValueError(f"Unsupported metadata format. Supported formats: {supported}")

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
            with connect(database_path) as connection:
                connection.execute(
                    """
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES (?, ?)
                    """,
                    ("metadata_format", metadata_format),
                )
                connection.commit()
            sync_training_metadata(database_path, dataset_path)
        except Exception:
            database_path.unlink(missing_ok=True)
            (dataset_path / "metadata.jsonl").unlink(missing_ok=True)
            raise

        return cls(
            path=database_path,
            name=clean_name,
            source_path=source_path,
            dataset_path=dataset_path,
            metadata_format=metadata_format,
        )

    @classmethod
    def open(cls, path: Path) -> Project:
        """Open a project and rebuild its manifest from the stored project captions."""
        database_path = Path(path).expanduser().resolve()
        metadata = read_project_metadata(database_path)
        root = database_path.parent
        source_path = root / "source"
        dataset_path = Path(metadata["dataset_path"]).expanduser().resolve()
        source_path.mkdir(exist_ok=True)
        dataset_path.mkdir(parents=True, exist_ok=True)

        metadata_format = read_metadata_format(database_path)
        sync_training_metadata(database_path, dataset_path)

        return cls(
            path=database_path,
            name=metadata["project_name"],
            source_path=source_path,
            dataset_path=dataset_path,
            metadata_format=metadata_format,
        )

    def statistics(self) -> dict[str, int]:
        """Return the dashboard counters for this project."""
        return read_project_statistics(self.path)
