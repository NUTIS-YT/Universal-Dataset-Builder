"""Configure and test an OpenAI-compatible VLM connection."""

from __future__ import annotations

from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from universal_dataset_builder.core.config import ConfigStore
from universal_dataset_builder.workers.vlm_connection_worker import VLMConnectionWorker


class VLMConnectionPage(QWidget):
    """Manage the user-local API endpoint and retrieve the available model IDs."""

    connection_saved = Signal()

    def __init__(self, config: ConfigStore) -> None:
        super().__init__()
        self.config = config
        self._worker: VLMConnectionWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("VLM Connection")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        description = QLabel(
            "Connect to an already-running OpenAI-compatible vision API, such as "
            "llama.cpp. Universal Dataset Builder does not download or launch models."
        )
        description.setObjectName("MutedText")
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.base_url_edit = QLineEdit(str(config.get("vlm_base_url", "")))
        self.base_url_edit.setPlaceholderText("http://127.0.0.1:8080/v1")
        form.addRow("API base URL", self.base_url_edit)

        self.api_key_edit = QLineEdit(str(config.get("vlm_api_key", "")))
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Optional API key")
        form.addRow("API key", self.api_key_edit)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 600)
        self.timeout_spin.setSuffix(" seconds")
        self.timeout_spin.setValue(int(config.get("vlm_timeout", 120)))
        form.addRow("Request timeout", self.timeout_spin)

        self.model_selector = QComboBox()
        self.model_selector.setMinimumContentsLength(24)
        self.model_selector.setEnabled(False)
        self._populate_models(
            list(config.get("vlm_models", [])),
            str(config.get("vlm_model", "")),
        )
        self.model_selector.currentIndexChanged.connect(self._save_selected_model)
        form.addRow("Active model", self.model_selector)
        layout.addLayout(form)

        key_note = QLabel(
            "The optional API key is saved in this computer's application config file. "
            "On Unix-like systems that file is restricted to the current user."
        )
        key_note.setObjectName("MutedText")
        key_note.setWordWrap(True)
        layout.addWidget(key_note)

        self.test_button = QPushButton("Test connection and load models")
        self.test_button.setObjectName("PrimaryButton")
        self.test_button.clicked.connect(self.test_connection)
        layout.addWidget(self.test_button)

        self.status_label = QLabel("Connection has not been tested.")
        self.status_label.setObjectName("MutedText")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

    def _populate_models(self, models: list[str], selected: str) -> None:
        self.model_selector.blockSignals(True)
        self.model_selector.clear()
        for model in models:
            self.model_selector.addItem(model, model)
        index = self.model_selector.findData(selected)
        if index < 0 and self.model_selector.count():
            index = 0
        self.model_selector.setCurrentIndex(index)
        self.model_selector.setEnabled(bool(models) and self._worker is None)
        self.model_selector.blockSignals(False)

    def test_connection(self) -> None:
        """Fetch /models in a worker thread and persist settings only on success."""
        if self._worker is not None:
            return

        worker = VLMConnectionWorker(
            self.base_url_edit.text(),
            self.api_key_edit.text(),
            self.timeout_spin.value(),
        )
        worker.signals.completed.connect(self._connection_succeeded)
        worker.signals.failed.connect(self._connection_failed)
        self._worker = worker
        self.test_button.setEnabled(False)
        self.status_label.setText("Connecting to the VLM API and retrieving models…")
        QThreadPool.globalInstance().start(worker)

    def _connection_succeeded(self, base_url: str, models: object) -> None:
        self._worker = None
        self.test_button.setEnabled(True)
        model_ids = models if isinstance(models, list) else []
        model_ids = [item for item in model_ids if isinstance(item, str)]

        previous_model = str(self.config.get("vlm_model", ""))
        self.config.set("vlm_base_url", base_url)
        self.config.set("vlm_api_key", self.api_key_edit.text())
        self.config.set("vlm_timeout", self.timeout_spin.value())
        self.config.set("vlm_models", model_ids)
        selected_model = previous_model if previous_model in model_ids else (
            model_ids[0] if model_ids else ""
        )
        self.config.set("vlm_model", selected_model)
        self.config.save()

        self.base_url_edit.setText(base_url)
        self._populate_models(model_ids, selected_model)
        if model_ids:
            self.status_label.setText(
                f"Connected successfully. {len(model_ids)} model(s) available."
            )
        else:
            self.status_label.setText(
                "The API responded successfully, but its /models list is empty."
            )
        self.connection_saved.emit()

    def _connection_failed(self, message: str) -> None:
        self._worker = None
        self.test_button.setEnabled(True)
        self.status_label.setText(f"Connection failed: {message}")

    def _save_selected_model(self, _index: int) -> None:
        model = self.model_selector.currentData()
        if isinstance(model, str) and model:
            self.config.set("vlm_model", model)
            self.config.save()
            self.connection_saved.emit()
