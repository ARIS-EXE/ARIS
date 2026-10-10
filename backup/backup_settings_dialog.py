from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from backup.backup_settings import (
    load_settings,
    save_settings,
)


class BackupSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            "Настройки резервного копирования"
        )
        self.setMinimumWidth(500)

        settings = load_settings()

        layout = QVBoxLayout(self)

        # Автоматическое резервное копирование
        self.enabled_checkbox = QCheckBox(
            "Включать автоматическое резервное копирование"
        )
        self.enabled_checkbox.setChecked(
            settings["enabled"]
        )

        layout.addWidget(
            self.enabled_checkbox
        )

        # Количество копий
        retention_layout = QHBoxLayout()

        retention_label = QLabel(
            "Хранить последних копий:"
        )

        self.retention_spinbox = QSpinBox()
        self.retention_spinbox.setMinimum(1)
        self.retention_spinbox.setMaximum(100)
        self.retention_spinbox.setValue(
            settings["retention_count"]
        )

        retention_layout.addWidget(
            retention_label
        )
        retention_layout.addWidget(
            self.retention_spinbox
        )
        retention_layout.addStretch()

        layout.addLayout(retention_layout)

        # Папка
        folder_label = QLabel(
            "Папка для резервных копий:"
        )

        layout.addWidget(folder_label)

        folder_layout = QHBoxLayout()

        self.folder_edit = QLineEdit(
            settings["backup_folder"]
        )

        browse_button = QPushButton(
            "Выбрать..."
        )
        browse_button.clicked.connect(
            self.select_folder
        )

        folder_layout.addWidget(
            self.folder_edit
        )
        folder_layout.addWidget(
            browse_button
        )

        layout.addLayout(folder_layout)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save
            | QDialogButtonBox.Cancel
        )

        buttons.accepted.connect(
            self.save
        )
        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(buttons)

    def select_folder(self):
        current_folder = self.folder_edit.text()

        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для резервных копий",
            current_folder
        )

        if folder:
            self.folder_edit.setText(folder)

    def save(self):
        folder = self.folder_edit.text().strip()

        if not folder:
            from app_paths import DEFAULT_BACKUP_DIR

            folder = str(DEFAULT_BACKUP_DIR)

        settings = {
            "enabled": self.enabled_checkbox.isChecked(),
            "retention_count": (
                self.retention_spinbox.value()
            ),
            "backup_folder": folder,
        }

        save_settings(settings)

        self.accept()