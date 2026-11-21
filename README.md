# Universal Dataset Builder

Universal Dataset Builder is a cross-platform desktop application for preparing image datasets and generating training captions through an external vision-language model (VLM) API.

The application stays independent of any particular VLM runtime or model trainer. It does not download model weights or launch inference servers: users connect to an already-running OpenAI-compatible API.

## Current status

The initial foundation includes a PySide6 desktop shell, dark and light themes, project creation and opening, a per-project SQLite database (project.fdb), separate source/ and dataset/ directories, dashboard statistics, automated tests, and GitHub Actions CI.

Image scanning, normalization, VLM integration, caption generation, dataset review, validation, and export are planned for later milestones.

## Requirements

- Python 3.12 or newer
- uv

## Development setup

    git clone https://github.com/NUTIS-YT/Universal-Dataset-Builder.git
    cd Universal-Dataset-Builder
    uv sync --all-groups
    uv run udb

Run tests and lint checks:

    uv run pytest
    uv run ruff check .

## Project layout

    MyDataset/
    ├── project.fdb       # SQLite project database
    ├── source/           # Original source images
    └── dataset/          # Normalized images and captions

The database stores project metadata, image records, captions, jobs, model profiles, and project settings. Application preferences are stored separately in the operating system's user configuration directory.

## Architecture

The code is organized under src/universal_dataset_builder/:

- core/ — application configuration and project lifecycle.
- gui/ — Qt main window, pages, and theme management.
- storage/ — SQLite schema and database access.

VLM inference will use an external OpenAI-compatible HTTP API. The application will not manage model downloads or server processes.

## Privacy and data safety

- Original source images remain separate from normalized dataset output.
- Project databases are local SQLite files.
- Future API credentials must remain in local configuration and must never be committed.
- Users are responsible for confirming that images are licensed for their intended training use. SFW classification alone does not grant usage rights.

## License

No license has been selected yet. Until one is added, standard copyright restrictions apply.
