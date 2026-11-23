# Universal Dataset Builder

[Русский](#русский) · [English](#english)

## Русский

Universal Dataset Builder — кроссплатформенное настольное приложение для подготовки наборов изображений и создания обучающих описаний с помощью внешнего API визуально-языковой модели (VLM).

Приложение не зависит от конкретной среды выполнения VLM или инструмента обучения моделей. Оно не скачивает веса моделей и не запускает серверы инференса: пользователь подключается к уже работающему API, совместимому с OpenAI.

### Текущий статус

Настольное приложение поддерживает создание и открытие проектов, отдельное хранилище SQLite для каждого проекта, тёмную и светлую темы, сканирование исходных изображений, браузер датасета (Dataset Browser), нормализатор изображений (Image Normalizer), управление подключением к VLM и пакетную генерацию описаний.

Сканер индексирует изображения PNG, JPEG, WEBP, BMP и TIFF, сохраняет их размеры, формат и SHA-256-хеши, помечает нечитаемые файлы и обрабатывает повторное сканирование без дублирования записей. Исходные файлы считываются непосредственно из исходного расположения и никогда не перемещаются и не изменяются.

Браузер датасета отображает миниатюры изображений, поддерживает поиск по имени файла и фильтрацию по статусу, открывает увеличенный предварительный просмотр, а также позволяет редактировать описания и проверять статус изображений. Описания и информация о проверке и модели хранятся в базе данных проекта. Приложение синхронизирует все подходящие пары «нормализованное изображение — описание» в единый манифест JSON Lines в формате UTF-8 по пути `dataset/metadata.jsonl`.

Манифест JSONL использует совместимые с инструментами обучения поля `image` и `prompt`. Пути к изображениям задаются относительно каталога `dataset/`; в манифест включаются только существующие нормализованные изображения с непустыми описаниями. Такой манифест можно напрямую использовать в инструментах обучения, например DiffSynth-Studio. Отдельные TXT-файлы с описаниями не создаются.

Нормализатор изображений преобразует проиндексированные исходные изображения в последовательность PNG-файлов, применяет ориентацию EXIF, преобразует встроенные цветовые профили в sRGB, обрабатывает прозрачность, обнаруживает точные дубликаты по пикселям и никогда не перезаписывает существующие выходные файлы. Нормализация выполняется в фоновом режиме и может быть отменена между обработкой отдельных изображений. После завершения операции манифест JSONL синхронизируется.

Подключение к VLM (VLM Connection) использует внешний API, совместимый с OpenAI. Оно получает список доступных идентификаторов моделей через `/models` и отправляет запросы с изображением и текстовым промптом на `/chat/completions`. Генератор описаний (Caption Generator) поддерживает режимы генерации для изображений без описаний и повторной генерации ещё не проверенных описаний, последовательную обработку, отображение прогресса, отмену между запросами и сохранение описаний вместе с метаданными. Сгенерированные описания остаются непроверенными, пока пользователь не примет или не отредактирует их в разделе Dataset.

В Caption Generator можно дополнительно включить референс персонажа на уровне проекта. Его описание помогает VLM сохранять постоянные особенности внешности персонажа при разных ракурсах, а триггерное слово автоматически добавляется в начало каждого сгенерированного описания. Эти параметры хранятся в `project.fdb` и также доступны через локальный API.

### Требования

- Python 3.12 или новее
- uv

### Настройка среды разработки

    git clone https://github.com/ericnorthwest/Universal-Dataset-Builder.git
    cd Universal-Dataset-Builder
    uv sync --all-groups
    uv run udb

В настольном лаунчере можно выбрать Legacy (PySide6) или Expressive UI Beta (Flutter).

При выборе Expressive лаунчер автоматически запускает локальный API, при первом использовании подготавливает нативную среду запуска Flutter, устанавливает необходимые зависимости Flutter и запускает интерфейс. Запускать API в отдельном терминале не требуется.

По умолчанию API слушает адрес `127.0.0.1:17891`. Он предназначен для локального настольного интерфейса. Не открывайте к нему сетевой доступ без предварительного добавления механизма аутентификации.

Для прямого запуска Legacy используйте:

    uv run udb-legacy

Для отладки только API используйте:

    uv run udb-api

Запуск тестов и проверок линтером:

    uv run pytest
    uv run ruff check .

### Expressive UI (бета-версия Flutter)

Отдельный настольный клиент на Flutter разрабатывается в каталоге `flutter_app/`. Он использует тот же локальный сервис FastAPI, что и интерфейс Legacy на PySide6, и не обращается напрямую к файлам SQLite проектов.

Первый этап Expressive включает Dashboard, Dataset Browser, Normalizer, Caption Generator (в том числе референс персонажа проекта), VLM Connection и настройки Appearance. Система анимации необязательна: пользователь может отключить анимации или выбрать профили Gentle и Expressive. Настройки темы и анимации хранятся локально, а настройки проекта — в `project.fdb`.

Инструкции по подготовке и запуску настольного клиента находятся в [flutter_app/README.md](flutter_app/README.md). Кратко: запустите `uv run udb-api` в одном терминале, а из каталога `flutter_app/` в другом выполните `flutter run -d linux` или `flutter run -d windows`.

### Структура проекта

    MyDataset/
    ├── project.fdb       # База данных проекта и состояние приложения
    ├── source/           # Исходные изображения
    └── dataset/
        ├── 00001.png
        ├── 00002.png
        └── metadata.jsonl  # Пары «изображение для обучения — описание»

Каждая строка JSONL содержит одну запись, например:

    {"image":"00001.png","prompt":"A character wearing a green robe."}
    {"image":"00002.png","prompt":"A close-up portrait with a gentle expression."}

При открытии существующего проекта Universal Dataset Builder заново формирует `metadata.jsonl` на основе описаний, сохранённых в `project.fdb`. В настоящее время в диалоге создания проекта доступен только формат метаданных JSONL.

### Архитектура

Код организован в каталоге `src/universal_dataset_builder/`:

- `core/` — конфигурация приложения и модели данных проекта.
- `dataset/` — сканирование исходных файлов, нормализация изображений и обучающие метаданные JSONL.
- `services/` — не зависящие от интерфейса сценарии работы с проектами, датасетами и описаниями, общие для разных интерфейсов.
- `gui/` — существующее главное окно PySide6, страницы, виджеты и управление темами.
- `storage/` — схема SQLite и доступ к базе данных.
- `vlm/` — клиент API, совместимого с OpenAI, и подготовка изображений.
- `workers/` — адаптеры PySide6, запускающие общие сервисы в фоновых потоках.
- `api/` — локальный интерфейс FastAPI и управляемые фоновые задачи, общие для интерфейсов, не использующих Qt.

Запросы к VLM API выполняются в рабочих потоках, поэтому сетевые операции не блокируют интерфейс. Приложение не управляет загрузкой моделей или серверными процессами. Настройки API хранятся в локальной конфигурации приложения пользователя; не сохраняйте рабочие секретные ключи на общедоступном или совместно используемом компьютере.

### Конфиденциальность и безопасность данных

- Исходные изображения хранятся отдельно от нормализованного набора данных.
- Нормализация никогда не перезаписывает существующие файлы в `dataset/`.
- Манифест JSONL записывается только в каталог `dataset/` соответствующего проекта.
- Базы данных проектов и настройки приложения хранятся в локальных файлах.
- API-ключи необязательны и отправляются только на настроенный конечный адрес API.
- Пользователь самостоятельно отвечает за проверку лицензий и наличия прав на изображения для предполагаемого использования при обучении. Одна лишь классификация SFW не предоставляет прав на использование изображений.

### Лицензия

Лицензия проекта пока не выбрана. До её добавления действуют стандартные ограничения авторского права.

## English

Universal Dataset Builder is a cross-platform desktop application for preparing image datasets and generating training captions through an external vision-language model (VLM) API.

The application stays independent of any particular VLM runtime or model trainer. It does not download model weights or launch inference servers: users connect to an already-running OpenAI-compatible API.

### Current status

The desktop application includes project creation and opening, per-project SQLite storage, dark and light themes, source image scanning, a Dataset Browser, an Image Normalizer, VLM connection management, and batch caption generation.

The scanner indexes PNG, JPEG, WEBP, BMP, and TIFF images, records dimensions, format and SHA-256 hashes, flags unreadable files, and handles repeat scans without duplicating records. Original source files are read in place and are never moved or modified.

The Dataset Browser displays image thumbnails, supports filename search and status filters, opens a larger image preview, and lets users edit captions and review image status. Captions and review/model information are stored in the project database. The application synchronizes all eligible normalized image/caption pairs into one UTF-8 JSON Lines manifest at dataset/metadata.jsonl.

The JSONL manifest uses the trainer-compatible fields image and prompt. Image paths are relative to dataset/, and only existing normalized images with non-empty captions are included. This can be used directly by training tools such as DiffSynth-Studio. Individual TXT caption sidecars are not created.

The Image Normalizer converts indexed source images to sequential PNG files, applies EXIF orientation, converts embedded color profiles to sRGB, handles transparency, detects exact pixel duplicates, and never overwrites existing output files. Normalization runs in the background and can be cancelled between images; after the operation, the JSONL manifest is synchronized.

VLM Connection uses an external OpenAI-compatible API. It retrieves available model IDs from /models and sends image-plus-prompt requests to /chat/completions. Caption Generator supports missing-caption and regenerate-unreviewed modes, sequential processing, progress reporting, cancellation between requests, and metadata-aware caption storage. Generated captions remain unreviewed until a person accepts or edits them in Dataset. An optional project-level character reference can be enabled in Caption Generator: its description guides the VLM to preserve stable identity traits across viewpoints, and its trigger word is automatically prepended to every generated caption. These options are stored in project.fdb and are also available through the local API.

### Requirements

- Python 3.12 or newer
- uv

### Development setup

    git clone https://github.com/ericnorthwest/Universal-Dataset-Builder.git
    cd Universal-Dataset-Builder
    uv sync --all-groups
    uv run udb

The desktop launcher lets you choose Legacy (PySide6) or Expressive UI Beta (Flutter).
When Expressive is selected, the launcher starts the local API automatically,
prepares the native Flutter runner on first use, resolves Flutter dependencies,
and starts the UI. You do not need to launch the API in a separate terminal.

The API listens on 127.0.0.1:17891 by default. It is intended for a local desktop
frontend; do not expose it to a network without adding an authentication layer.

For direct Legacy startup, use:

    uv run udb-legacy

For API-only debugging, use:

    uv run udb-api

Run tests and lint checks:

    uv run pytest
    uv run ruff check .

### Expressive UI (Flutter beta)

A separate Flutter desktop client is being developed in `flutter_app/`. It uses the same local FastAPI service as the Legacy PySide6 interface and does not access project SQLite files directly.

The first Expressive milestone includes Dashboard, Dataset Browser, Normalizer, Caption Generator (including project character reference), VLM Connection, and Appearance settings. Its motion system is optional: users can disable animations or choose Gentle and Expressive profiles. Theme and motion preferences are stored locally; project settings remain in `project.fdb`.

To prepare and run the desktop client, see [flutter_app/README.md](flutter_app/README.md). In short, start `uv run udb-api` in one terminal and run `flutter run -d linux` or `flutter run -d windows` from `flutter_app/` in another.

### Project layout

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

### Architecture

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

### Privacy and data safety

- Original source images remain separate from normalized dataset output.
- Normalization never overwrites an existing file in dataset/.
- The JSONL manifest is written only within the project dataset directory.
- Project databases and application settings are local files.
- API keys are optional and are sent only to the configured endpoint.
- Users are responsible for confirming that images are licensed for their intended training use. SFW classification alone does not grant usage rights.

### License

No license has been selected yet. Until one is added, standard copyright restrictions apply.
