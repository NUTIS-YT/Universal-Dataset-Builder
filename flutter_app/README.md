# Expressive UI (Flutter)

This is the Flutter desktop front end for Universal Dataset Builder. It talks to the shared local FastAPI service; it does not open the SQLite project database directly.

## Requirements

- Flutter 3.50 or newer (stable)
- The Python environment for Universal Dataset Builder
- Linux desktop prerequisites on Linux: `clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev`
- Visual Studio with the Desktop development with C++ workload on Windows

## Add desktop runner folders

From this directory, generate the native desktop runner folders once:

```bash
flutter create --platforms=linux,windows --project-name universal_dataset_builder_expressive --org com.ericnorthwest --no-pub .
flutter pub get
```

The command adds the requested desktop platform folders to this existing Flutter app. Keep the generated `linux/` and `windows/` runner files when building locally.

## Run in development

Terminal 1, from the repository root:

```bash
uv sync --all-groups
uv run udb-api
```

Terminal 2, from `flutter_app/`:

```bash
flutter run -d linux
```

On Windows, use:

```powershell
flutter run -d windows
```

The local API defaults to `http://127.0.0.1:17891`. The address can be changed in VLM Connection. Keep the Python API and Flutter UI on the same computer unless the backend is separately secured.

## Build

```bash
flutter build linux --release
```

or:

```powershell
flutter build windows --release
```

## Motion preferences

Appearance includes a global animation switch and two motion profiles:

- **Gentle** uses shorter, less prominent transitions.
- **Expressive** enables the fuller page, card, and section animations.
- Turning animations off removes the optional transitions. System reduced-motion preferences are also respected.

Theme and motion preferences are stored locally on the desktop. Project content and character-reference settings remain in the Python project's `project.fdb`.
