# Universal Dataset Builder

Universal Dataset Builder is a cross-platform desktop application for preparing image datasets and generating training captions through an external vision-language model (VLM) API.

The application stays independent of any particular VLM runtime or model trainer. It does not download model weights or launch inference servers: users connect to an already-running OpenAI-compatible API.

## Current status

The desktop application includes project creation and opening, per-project SQLite storage, dark and light themes, source image scanning, and a Dataset Browser.

The scanner indexes PNG, JPEG, WEBP, BMP, and TIFF images, records dimensions, format and SHA-256 hashes, flags unreadable files, and handles repeat scans without duplicating records. Original source files are read in place and are never moved or modified.

The Dataset Browser displays image thumbnails, supports filename search and status filters, opens a larger image preview, and lets users edit captions and review image status. Captions are stored in the project database. When a normalized image already exists inside dataset/, saving its caption also writes a neighboring UTF-8 TXT file.

Image normalization, VLM API integration, automated caption generation, validation, and export are the next development milestones.

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
- gui/ — Qt main window, pages, widgets, and theme management.
- dataset/ — source scanning and caption sidecar handling.
- storage/ — SQLite schema and database access.
- workers/ — background operations coordinated with the GUI.

VLM inference will use an external OpenAI-compatible HTTP API. The application will not manage model downloads or server processes.

## Privacy and data safety

- Original source images remain separate from normalized dataset output.
- Caption sidecars are written only within the project dataset directory.
- Project databases are local SQLite files.
- Future API credentials must remain in local configuration and must never be committed.
- Users are responsible for confirming that images are licensed for their intended training use. SFW classification alone does not grant usage rights.

## License

No license has been selected yet. Until one is added, standard copyright restrictions apply.
