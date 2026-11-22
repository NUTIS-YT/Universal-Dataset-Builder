# Universal Dataset Builder

Universal Dataset Builder is a cross-platform desktop application for preparing image datasets and generating training captions through an external vision-language model (VLM) API.

The application stays independent of any particular VLM runtime or model trainer. It does not download model weights or launch inference servers: users connect to an already-running OpenAI-compatible API.

## Current status

The desktop application includes project creation and opening, per-project SQLite storage, dark and light themes, source image scanning, a Dataset Browser, an Image Normalizer, VLM connection management, and batch caption generation.

The scanner indexes PNG, JPEG, WEBP, BMP, and TIFF images, records dimensions, format and SHA-256 hashes, flags unreadable files, and handles repeat scans without duplicating records. Original source files are read in place and are never moved or modified.

The Dataset Browser displays image thumbnails, supports filename search and status filters, opens a larger image preview, and lets users edit captions and review image status. Captions and review/model information are stored in the project database. The application synchronizes all eligible normalized image/caption pairs into one UTF-8 JSON Lines manifest at dataset/metadata.jsonl.

The JSONL manifest uses the trainer-compatible fields image and prompt. Image paths are relative to dataset/, and only existing normalized images with non-empty captions are included. This can be used directly by training tools such as DiffSynth-Studio. Individual TXT caption sidecars are not created.

The Image Normalizer converts indexed source images to sequential PNG files, applies EXIF orientation, converts embedded color profiles to sRGB, handles transparency, detects exact pixel duplicates, and never overwrites existing output files. Normalization runs in the background and can be cancelled between images; after the operation, the JSONL manifest is synchronized.

VLM Connection uses an external OpenAI-compatible API. It retrieves available model IDs from /models and sends image-plus-prompt requests to /chat/completions. Caption Generator supports missing-caption and regenerate-unreviewed modes, sequential processing, progress reporting, cancellation between requests, and metadata-aware caption storage. Generated captions remain unreviewed until a person accepts or edits them in Dataset. An optional project-level character reference can be enabled in Caption Generator: its description guides the VLM to preserve stable identity traits across viewpoints, and its trigger word is automatically prepended to every generated caption. These options are stored in project.fdb and are also available through the local API.

## Requirements

- Python 3.12 or newer
- uv

## Development setup

    git clone https://github.com/ericnorthwest/Universal-Dataset-Builder.git
    cd Universal-Dataset-Builder
    uv sync --all-groups
    uv run udb

Start the local API server used by the Expressive UI:

    uv run udb-api

The API listens on 127.0.0.1:17891 by default. It is intended for a local desktop
frontend; do not expose it to a network without adding an authentication layer.

Run tests and lint checks:

    uv run pytest
    uv run ruff check .

## Expressive UI (Flutter beta)

A separate Flutter desktop client is being developed in `flutter_app/`. It uses the same local FastAPI service as the Legacy PySide6 interface and does not access project SQLite files directly.

The first Expressive milestone includes Dashboard, Dataset Browser, Normalizer, Caption Generator (including project character reference), VLM Connection, and Appearance settings. Its motion system is optional: users can disable animations or choose Gentle and Expressive profiles. Theme and motion preferences are stored locally; project settings remain in `project.fdb`.

To prepare and run the desktop client, see [flutter_app/README.md](flutter_app/README.md). In short, start `uv run udb-api` in one terminal and run `flutter run -d linux` or `flutter run -d windows` from `flutter_app/` in another.

## Project layout

    MyDataset/
    ├── project.fdb       # Project database and application state
    ├── source/           # Original source images
    └── dataset/
        ├── 00001.png
        ├── 00002.png
        └── metadata.jsonl  # Training image/caption pairs

Each JSONL line contains one record, for example:

    {"image":"00001.png","prompt":"A character wearing a green robe."}
    {"image":"00002.png","prompt":"A close-up portrait with a gentle expression."}

When an existing project is opened, Universal Dataset Builder rebuilds metadata.jsonl from captions stored in project.fdb. The project creation dialog currently offers JSONL as the only metadata format.

## Architecture

The code is organized under src/universal_dataset_builder/:

- core/ — application configuration and project data models.
- dataset/ — source scanning, image normalization, and JSONL training metadata.
- services/ — UI-independent project, dataset, and caption workflows shared by front ends.
- gui/ — the existing PySide6 main window, pages, widgets, and theme management.
- storage/ — SQLite schema and database access.
- vlm/ — OpenAI-compatible API client and image preparation.
- workers/ — PySide6 adapters that run shared services in background threads.
- api/ — local FastAPI interface and managed background jobs shared with non-Qt front ends.

VLM API requests are executed in worker threads so network operations do not freeze the interface. The application does not manage model downloads or server processes. API settings are stored in the user's local application configuration; avoid saving a production secret on a shared computer.

## Privacy and data safety

- Original source images remain separate from normalized dataset output.
- Normalization never overwrites an existing file in dataset/.
- The JSONL manifest is written only within the project dataset directory.
- Project databases and application settings are local files.
- API keys are optional and are sent only to the configured endpoint.
- Users are responsible for confirming that images are licensed for their intended training use. SFW classification alone does not grant usage rights.

## License

No license has been selected yet. Until one is added, standard copyright restrictions apply.
