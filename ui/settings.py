
import sqlite3
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QInputDialog,
    QMessageBox,
)

from app_paths import DB_PATH


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_window = parent

        self.setWindowTitle("Настройки")
        self.resize(800, 500)
        self.setMinimumSize(700, 400)

        main_layout = QHBoxLayout(self)

        # Левая панель навигации
        navigation_layout = QVBoxLayout()
        navigation_layout.setSpacing(6)

        navigation_title = QLabel("Разделы")
        navigation_title.setStyleSheet(
            "font-size: 16px; font-weight: bold;"
        )
        navigation_layout.addWidget(navigation_title)

        self.delivery_button = QPushButton(
            "Доставка и упаковка"
        )
        self.backup_button = QPushButton(
            "Резервное копирование"
        )

        for button in (
            self.delivery_button,
            self.backup_button,
        ):
            button.setFixedWidth(190)
            button.setMinimumHeight(36)
            navigation_layout.addWidget(button)

        navigation_layout.addStretch()

        # Область страниц
        self.pages = QStackedWidget()

        # Страница доставки и упаковки
        delivery_page = QWidget()
        delivery_layout = QVBoxLayout(delivery_page)

        delivery_title = QLabel(
            "Доставка и упаковка"
        )
        delivery_title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )
        delivery_layout.addWidget(delivery_title)

        self.delivery_table = QTableWidget()
        self.delivery_table.setColumnCount(3)
        self.delivery_table.setHorizontalHeaderLabels([
            "Название",
            "Доставка",
            "Упаковка",
        ])
        self.delivery_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.delivery_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.delivery_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.delivery_table.verticalHeader().setVisible(False)

        header = self.delivery_table.horizontalHeader()
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents
        )

        delivery_layout.addWidget(self.delivery_table)

        delivery_buttons_layout = QHBoxLayout()

        add_delivery_button = QPushButton("Добавить")
        delete_delivery_button = QPushButton("Удалить")

        add_delivery_button.clicked.connect(
            self.add_delivery_option
        )
        delete_delivery_button.clicked.connect(
            self.delete_delivery_option
        )

        delivery_buttons_layout.addWidget(
            add_delivery_button
        )
        delivery_buttons_layout.addWidget(
            delete_delivery_button
        )
        delivery_buttons_layout.addStretch()

        delivery_layout.addLayout(delivery_buttons_layout)

        # Страница резервного копирования
        backup_page = QWidget()
        backup_layout = QVBoxLayout(backup_page)

        backup_title = QLabel(
            "Резервное копирование"
        )
        backup_title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )
        backup_layout.addWidget(backup_title)

        backup_layout.addWidget(
            QLabel(
                "Создание и восстановление резервных копий "
                "базы данных."
            )
        )

        create_backup_button = QPushButton(
            "Создать резервную копию"
        )
        restore_backup_button = QPushButton(
            "Восстановить из резервной копии"
        )
        backup_settings_button = QPushButton(
            "Настроить резервное копирование"
        )

        create_backup_button.clicked.connect(
            self.create_backup
        )
        restore_backup_button.clicked.connect(
            self.restore_backup
        )
        backup_settings_button.clicked.connect(
            self.open_backup_settings
        )

        backup_layout.addWidget(create_backup_button)
        backup_layout.addWidget(restore_backup_button)
        backup_layout.addWidget(backup_settings_button)
        backup_layout.addStretch()

        # Добавляем страницы
        self.pages.addWidget(delivery_page)
        self.pages.addWidget(backup_page)

        self.delivery_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(0)
        )
        self.backup_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(1)
        )

        main_layout.addLayout(navigation_layout)
        main_layout.addWidget(self.pages, 1)

        self.load_delivery_options()

    def load_delivery_options(self):
        with sqlite3.connect(DB_PATH) as connection:
            rows = connection.execute(
                """
                SELECT id, name, shipping_cost, packaging_cost
                FROM delivery_options
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()

        self.delivery_table.setRowCount(0)

        for option_id, name, shipping_cost, packaging_cost in rows:
            row = self.delivery_table.rowCount()
            self.delivery_table.insertRow(row)

            name_item = QTableWidgetItem(name)
            name_item.setData(
                Qt.ItemDataRole.UserRole,
                option_id
            )

            shipping_item = QTableWidgetItem(
                f"{shipping_cost} ₽"
            )
            packaging_item = QTableWidgetItem(
                f"{packaging_cost} ₽"
            )

            self.delivery_table.setItem(
                row, 0, name_item
            )
            self.delivery_table.setItem(
                row, 1, shipping_item
            )
            self.delivery_table.setItem(
                row, 2, packaging_item
            )

    def add_delivery_option(self):
        name, ok = QInputDialog.getText(
            self,
            "Новый вариант",
            "Название варианта доставки и упаковки:"
        )

        if not ok:
            return

        name = name.strip()

        if not name:
            QMessageBox.warning(
                self,
                "Пустое название",
                "Введите название варианта."
            )
            return

        shipping_cost, ok = QInputDialog.getInt(
            self,
            "Стоимость доставки",
            "Стоимость доставки (₽):",
            0,
            0,
            100000000
        )

        if not ok:
            return

        packaging_cost, ok = QInputDialog.getInt(
            self,
            "Стоимость упаковки",
            "Стоимость упаковки (₽):",
            0,
            0,
            100000000
        )

        if not ok:
            return

        try:
            with sqlite3.connect(DB_PATH) as connection:
                connection.execute(
                    """
                    INSERT INTO delivery_options
                        (name, shipping_cost, packaging_cost)
                    VALUES (?, ?, ?)
                    """,
                    (name, shipping_cost, packaging_cost)
                )

        except sqlite3.Error as error:
            QMessageBox.critical(
                self,
                "Ошибка базы данных",
                f"Не удалось добавить вариант:\n{error}"
            )
            return

        self.load_delivery_options()

    def delete_delivery_option(self):
        row = self.delivery_table.currentRow()

        if row < 0:
            QMessageBox.information(
                self,
                "Удаление варианта",
                "Сначала выберите вариант в таблице."
            )
            return

        name_item = self.delivery_table.item(row, 0)
        option_id = name_item.data(
            Qt.ItemDataRole.UserRole
        )
        name = name_item.text()

        answer = QMessageBox.question(
            self,
            "Удаление варианта",
            f"Удалить вариант «{name}»?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            with sqlite3.connect(DB_PATH) as connection:
                connection.execute(
                    """
                    DELETE FROM delivery_options
                    WHERE id = ?
                    """,
                    (option_id,)
                )

        except sqlite3.Error as error:
            QMessageBox.critical(
                self,
                "Ошибка базы данных",
                f"Не удалось удалить вариант:\n{error}"
            )
            return

        self.load_delivery_options()

    def create_backup(self):
        self.main_window.create_backup()

    def restore_backup(self):
        self.main_window.restore_backup()

    def open_backup_settings(self):
        from backup.backup_settings_dialog import (
            BackupSettingsDialog,
        )

        dialog = BackupSettingsDialog(self)
        dialog.exec()
