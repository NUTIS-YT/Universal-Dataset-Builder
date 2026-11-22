"""Batch caption generator UI for the configured vision-language model."""

from __future__ import annotations

from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from universal_dataset_builder.core.config import ConfigStore
from universal_dataset_builder.core.project import Project
from universal_dataset_builder.storage.database import (
    read_caption_character_settings,
    save_caption_character_settings,
)
from universal_dataset_builder.workers.caption_worker import CaptionSummary, CaptionWorker


class CaptionGeneratorPage(QWidget):
    """Generate captions for indexed images using the saved external VLM API."""

    generation_completed = Signal()

    def __init__(self, config: ConfigStore) -> None:
        super().__init__()
        self.config = config
        self.project: Project | None = None
        self._worker: CaptionWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Caption Generator")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.connection_label = QLabel("")
        self.connection_label.setObjectName("MutedText")
        self.connection_label.setWordWrap(True)
        layout.addWidget(self.connection_label)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.model_selector = QComboBox()
        self.model_selector.currentIndexChanged.connect(self._save_model)
        form.addRow("VLM model", self.model_selector)

        self.selection_selector = QComboBox()
        self.selection_selector.addItem("Only images without captions", "missing")
        self.selection_selector.addItem(
            "Regenerate all unreviewed captions",
            "unreviewed",
        )
        form.addRow("Images to process", self.selection_selector)

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 100_000)
        self.limit_spin.setValue(0)
        self.limit_spin.setSpecialValueText("All eligible images")
        form.addRow("Maximum images", self.limit_spin)
        layout.addLayout(form)

        prompt_title = QLabel("Caption prompt")
        prompt_title.setObjectName("SectionTitle")
        layout.addWidget(prompt_title)

        self.prompt_editor = QTextEdit()
        self.prompt_editor.setPlainText(str(config.get("caption_prompt", "")))
        self.prompt_editor.setMinimumHeight(120)
        layout.addWidget(self.prompt_editor, 1)

        character_title = QLabel("Character consistency")
        character_title.setObjectName("SectionTitle")
        layout.addWidget(character_title)

        self.character_reference_checkbox = QCheckBox(
            "Use character reference for this project"
        )
        self.character_reference_checkbox.toggled.connect(
            self._save_character_settings
        )
        layout.addWidget(self.character_reference_checkbox)

        self.character_fields = QWidget()
        character_form = QFormLayout(self.character_fields)
        character_form.setContentsMargins(0, 0, 0, 0)
        character_form.setHorizontalSpacing(18)
        character_form.setVerticalSpacing(8)

        self.character_description_editor = QTextEdit()
        self.character_description_editor.setPlaceholderText(
            "Describe stable identity traits: species, colors, markings, face, "
            "hair, characteristic accessories, and other details that should remain "
            "consistent across viewpoints."
        )
        self.character_description_editor.setMinimumHeight(84)
        self.character_description_editor.textChanged.connect(
            self._save_character_settings
        )
        character_form.addRow("Character information", self.character_description_editor)

        self.trigger_word_edit = QLineEdit()
        self.trigger_word_edit.setMaxLength(512)
        self.trigger_word_edit.setPlaceholderText("e.g. my_character")
        self.trigger_word_edit.textChanged.connect(self._save_character_settings)
        character_form.addRow("Trigger word", self.trigger_word_edit)
        layout.addWidget(self.character_fields)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Create or open a project and configure a VLM connection.")
        self.status_label.setObjectName("MutedText")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.generate_button = QPushButton("Generate captions")
        self.generate_button.setObjectName("PrimaryButton")
        self.generate_button.clicked.connect(self.start_generation)
        layout.addWidget(self.generate_button)

        self.cancel_button = QPushButton("Cancel after current image")
        self.cancel_button.clicked.connect(self.cancel_generation)
        self.cancel_button.setVisible(False)
        layout.addWidget(self.cancel_button)

        self.refresh_connection()
        self._update_controls()

    def set_project(self, project: Project | None) -> None:
        """Attach the active project."""
        self.project = project
        self._load_character_settings()
        if project is None:
            self.status_label.setText("Create or open a project before generating captions.")
        else:
            self.status_label.setText("Ready to generate captions for this project.")
        self._update_controls()

    def _load_character_settings(self) -> None:
        """Load character-reference settings from the currently opened project."""
        self._loading_character_settings = True
        try:
            settings = (
                read_caption_character_settings(self.project.path)
                if self.project is not None
                else {"enabled": False, "description": "", "trigger_word": ""}
            )
            self.character_reference_checkbox.setChecked(bool(settings["enabled"]))
            self.character_description_editor.setPlainText(str(settings["description"]))
            self.trigger_word_edit.setText(str(settings["trigger_word"]))
        finally:
            self._loading_character_settings = False
        self._update_character_controls()

    def _update_character_controls(self) -> None:
        has_project = self.project is not None
        self.character_reference_checkbox.setEnabled(has_project)
        self.character_fields.setEnabled(
            has_project and self.character_reference_checkbox.isChecked()
        )

    def _save_character_settings(self, _value: object = None) -> None:
        """Autosave changes directly into the active project's SQLite file."""
        self._update_character_controls()
        if self.project is None or getattr(self, "_loading_character_settings", False):
            return
        try:
            save_caption_character_settings(
                self.project.path,
                enabled=self.character_reference_checkbox.isChecked(),
                description=self.character_description_editor.toPlainText(),
                trigger_word=self.trigger_word_edit.text(),
            )
        except (OSError, ValueError) as error:
            self.character_reference_checkbox.setToolTip(
                f"Could not save project character settings: {error}"
            )
        else:
            self.character_reference_checkbox.setToolTip(
                "Character settings are saved in this project's project.fdb file."
            )

    def refresh_connection(self) -> None:
        """Reload the available model list after a connection change."""
        selected = str(self.config.get("vlm_model", ""))
        models = list(self.config.get("vlm_models", []))
        if selected and selected not in models:
            models.append(selected)

        self.model_selector.blockSignals(True)
        self.model_selector.clear()
        for model in models:
            if isinstance(model, str) and model:
                self.model_selector.addItem(model, model)
        index = self.model_selector.findData(selected)
        if index >= 0:
            self.model_selector.setCurrentIndex(index)
        elif self.model_selector.count():
            self.model_selector.setCurrentIndex(0)
        self.model_selector.blockSignals(False)

        base_url = str(self.config.get("vlm_base_url", ""))
        if base_url and self.model_selector.count():
            self.connection_label.setText(f"Connected endpoint: {base_url}")
        else:
            self.connection_label.setText(
                "No model available. Open VLM Connection and test the API first."
            )
        self._update_controls()

    def _save_model(self, _index: int) -> None:
        model = self.model_selector.currentData()
        if isinstance(model, str) and model:
            self.config.set("vlm_model", model)
            self.config.save()

    def _update_controls(self) -> None:
        self._update_character_controls()
        busy = self._worker is not None
        ready = bool(
            self.project is not None
            and self.model_selector.currentData()
            and self.config.get("vlm_base_url")
        )
        self.generate_button.setEnabled(ready and not busy)
        self.generate_button.setText("Generating…" if busy else "Generate captions")
        self.cancel_button.setVisible(busy)
        self.cancel_button.setEnabled(busy)

    def start_generation(self) -> None:
        """Persist the prompt and start the background caption worker."""
        if self.project is None or self._worker is not None:
            return

        prompt = self.prompt_editor.toPlainText().strip()
        model = self.model_selector.currentData()
        if not prompt:
            self.status_label.setText("Enter a caption prompt before starting.")
            return
        if not isinstance(model, str) or not model:
            self.status_label.setText("Select a model in VLM Connection first.")
            return

        self._save_character_settings()
        self.config.set("caption_prompt", prompt)
        self.config.set("vlm_model", model)
        self.config.save()

        worker = CaptionWorker(
            self.project.path,
            self.project.source_path,
            self.project.dataset_path,
            base_url=str(self.config.get("vlm_base_url")),
            api_key=str(self.config.get("vlm_api_key", "")),
            timeout_seconds=int(self.config.get("vlm_timeout", 120)),
            model=model,
            prompt=prompt,
            selection_mode=str(self.selection_selector.currentData()),
            limit=self.limit_spin.value(),
        )
        worker.signals.progress.connect(self._update_progress)
        worker.signals.completed.connect(self._generation_finished)
        worker.signals.failed.connect(self._generation_failed)
        self._worker = worker
        self.progress.setRange(0, 0)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.status_label.setText("Preparing caption generation…")
        self._update_controls()
        QThreadPool.globalInstance().start(worker)

    def cancel_generation(self) -> None:
        """Request cancellation between image requests."""
        if self._worker is not None:
            self._worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancellation requested. Finishing current image…")

    def _update_progress(self, current: int, total: int, filename: str) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(current)
        self.status_label.setText(
            f"Generating caption for {filename} · {current}/{total}"
        )

    def _generation_finished(self, result: object) -> None:
        self._worker = None
        self.progress.setVisible(False)
        self._update_controls()
        if not isinstance(result, CaptionSummary):
            self.status_label.setText("Caption generation returned an invalid result.")
            return

        state = "Cancelled" if result.cancelled else "Complete"
        self.status_label.setText(
            f"{state}: {result.generated} generated · {result.failed} failed "
            f"· {result.discovered} selected."
        )
        details = list(result.failed_files)
        if result.metadata_warning:
            details.append(f"metadata.jsonl: {result.metadata_warning}")
            self.status_label.setText(
                self.status_label.text() + " JSONL update warning."
            )
        self.status_label.setToolTip("\n".join(details[:20]))
        self.generation_completed.emit()

    def _generation_failed(self, message: str) -> None:
        self._worker = None
        self.progress.setVisible(False)
        self._update_controls()
        self.status_label.setText(f"Caption generation failed: {message}")
