# Furry Dataset Builder

Furry Dataset Builder (FDB) is a cross-platform desktop application for preparing image datasets and generating training captions through an external vision-language model (VLM) API.

The application is designed to stay independent of any particular VLM runtime or LoRA trainer. It does not download model weights or launch inference servers: users connect to an already-running OpenAI-compatible API.

## Project status

The project is under active development. The current milestone establishes the desktop application foundation and navigation shell. Dataset processing, project management, and VLM integration are being implemented incrementally.

## Planned capabilities

- Project-based datasets backed by SQLite.
- Safe image scanning and PNG normalization.
- Sequential image names such as `00001.png`.
- Caption generation through an external OpenAI-compatible vision API.
- Caption review and editing.
- Dataset validation and export.
- Resumable background processing.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)

## Development setup

```bash
git clone https://github.com/NUTIS-YT/Universal-Dataset-Builder.git
cd Universal-Dataset-Builder
uv sync --group dev
uv run fdb
```

Run tests:

```bash
uv run pytest
```

## Architecture

The code lives in `src/furry_dataset_builder/` and is separated into core application services, Qt GUI, dataset processing, inference, captions, storage, and workers. The UI is built with PySide6; application settings are stored as JSON and project data will use SQLite.

## Configuration and privacy

FDB connects only to the VLM endpoint explicitly configured by the user. API keys are stored in the local application configuration and are never committed to the repository. Do not share configuration files containing credentials.

## License

No license has been selected yet. Until one is added, standard copyright restrictions apply.
