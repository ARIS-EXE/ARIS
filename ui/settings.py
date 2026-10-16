from models.commission_formula import (
    evaluate_formula,
    FormulaError,
    VARIABLES,
)
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
    QLineEdit,
    QGridLayout,
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
        self.commission_formula_button = QPushButton(
            "Формула комиссии"
        )
        for button in (
            self.delivery_button,
            self.backup_button,
            self.commission_formula_button,
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

        # Страница формулы комиссии
        formula_page = QWidget()
        formula_layout = QVBoxLayout(formula_page)

        formula_title = QLabel("Формула комиссии")
        formula_title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )
        formula_layout.addWidget(formula_title)

        formula_layout.addWidget(
            QLabel(
                "Соберите формулу кнопками ниже. "
                "Например, для комиссии 10% от цены продажи: "
                "Цена продажи × 10 %."
            )
        )

        self.commission_formula_input = QLineEdit()
        self.commission_formula_input.setReadOnly(True)
        self.commission_formula_input.setPlaceholderText(
            "Нажимайте кнопки, чтобы собрать формулу"
        )
        formula_layout.addWidget(self.commission_formula_input)

        variables_layout = QGridLayout()

        formula_variables = [
            ("Цена продажи", "sale_price"),
            ("Цена производителя", "manufacturer_price"),
            ("Закупочная стоимость", "purchase_price"),
            ("Доставка при закупке", "purchase_shipping"),
            ("Расходы на упаковку", "packaging"),
            ("Доставка покупателю", "buyer_shipping"),
        ]

        for index, (label, variable) in enumerate(formula_variables):
            button = QPushButton(label)
            button.clicked.connect(
                lambda checked=False, value=variable:
                self.insert_formula_text(value)
            )
            variables_layout.addWidget(
                button,
                index // 2,
                index % 2
            )

        formula_layout.addLayout(variables_layout)


        operators_layout = QGridLayout()
        operators_layout.setSpacing(6)

        operator_buttons = [
            ("7", "7"),
            ("8", "8"),
            ("9", "9"),
            ("÷", " / "),
            ("4", "4"),
            ("5", "5"),
            ("6", "6"),
            ("×", " * "),
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("−", " - "),
            (".", "."),
            ("0", "0"),
            ("%", " / 100"),
            ("+", " + "),
            ("(", "("),
            (")", ")"),
        ]

        for index, (label, value) in enumerate(operator_buttons):
            button = QPushButton(label)
            button.setMinimumSize(55, 34)

            button.clicked.connect(
                lambda checked=False, text=value:
                self.insert_formula_text(text)
            )

            operators_layout.addWidget(
                button,
                index // 4,
                index % 4
            )

        formula_layout.addLayout(operators_layout)


        formula_actions = QHBoxLayout()

        clear_formula_button = QPushButton("Очистить")
        clear_formula_button.clicked.connect(
            self.commission_formula_input.clear
        )

        save_formula_button = QPushButton("Сохранить формулу")
        save_formula_button.clicked.connect(
            self.save_commission_formula
        )

        formula_actions.addWidget(clear_formula_button)
        formula_actions.addWidget(save_formula_button)

        formula_layout.addLayout(formula_actions)

        self.formula_example_label = QLabel()
        self.formula_example_label.setWordWrap(True)
        formula_layout.addWidget(self.formula_example_label)

        formula_layout.addStretch()

        # Добавляем страницы
        self.pages.addWidget(delivery_page)
        self.pages.addWidget(backup_page)
        self.pages.addWidget(formula_page)
        self.delivery_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(0)
        )
        self.backup_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(1)
        )
        self.commission_formula_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(2)
        )
        main_layout.addLayout(navigation_layout)
        main_layout.addWidget(self.pages, 1)

        self.load_delivery_options()
        self.load_commission_formula()
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
                str(shipping_cost)
            )
            packaging_item = QTableWidgetItem(
                str(packaging_cost)
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
            "Стоимость доставки :",
            0,
            0,
            100000000
        )

        if not ok:
            return

        packaging_cost, ok = QInputDialog.getInt(
            self,
            "Стоимость упаковки",
            "Стоимость упаковки :",
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

    def insert_formula_text(self, text):
        current = self.commission_formula_input.text()
        self.commission_formula_input.setText(current + text)

    def save_commission_formula(self):
        from database.database import get_connection

        formula = self.commission_formula_input.text().strip()

        if not formula:
            QMessageBox.warning(
                self,
                "Формула комиссии",
                "Сначала соберите формулу."
            )
            return
        # Проверяем формулу и наличие только разрешённых переменных.
        try:
            test_values = {
                name: 100
                for name in VARIABLES
            }
            evaluate_formula(formula, test_values)

        except FormulaError as error:
            QMessageBox.warning(
                self,
                "Некорректная формула",
                str(error)
            )
            return
        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES ('commission_formula', ?)
                ON CONFLICT(key)
                DO UPDATE SET value = excluded.value
                """,
                (formula,)
            )
            connection.commit()
        except Exception as error:
            connection.rollback()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить формулу:\n{error}"
            )
            return
        finally:
            connection.close()
        self.load_commission_formula_example()
        QMessageBox.information(
            self,
            "Формула комиссии",
            "Формула сохранена."
        )

    def load_commission_formula(self):
        from database.database import get_connection

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT value
                FROM app_settings
                WHERE key = 'commission_formula'
                """
            )
            row = cursor.fetchone()
        finally:
            connection.close()

        formula = row[0] if row else ""
        self.commission_formula_input.setText(formula)

        self.load_commission_formula_example()

    def load_commission_formula_example(self):
        from database.database import get_connection
        from models.commission_formula import (
            evaluate_formula,
            FormulaError,
            VARIABLES,
        )

        formula = self.commission_formula_input.text().strip()

        if not formula:
            self.formula_example_label.setText(
                "Сначала составьте и сохраните формулу."
            )
            return

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT
                    si.sale_price,
                    p.manufacturer_price,
                    i.purchase_price,
                    i.purchase_shipping,
                    si.packaging,
                    si.buyer_shipping,
                    si.commission,
                    i.internal_number
                FROM sale_items si
                JOIN instances i ON i.id = si.instance_id
                JOIN products p ON p.id = i.product_id
                WHERE si.active = 1
                  AND si.sale_price IS NOT NULL
                  AND p.manufacturer_price IS NOT NULL
                  AND i.purchase_price IS NOT NULL
                  AND i.purchase_shipping IS NOT NULL
                  AND si.packaging IS NOT NULL
                  AND si.buyer_shipping IS NOT NULL
                ORDER BY RANDOM()
                """
            )
            rows = cursor.fetchall()
        finally:
            connection.close()

        if not rows:
            self.formula_example_label.setText(
                "Нет проданных экземпляров с заполненными данными "
                "для примера."
            )
            return

        variable_values = {
            "sale_price": 0,
            "manufacturer_price": 1,
            "purchase_price": 2,
            "purchase_shipping": 3,
            "packaging": 4,
            "buyer_shipping": 5,
        }

        for row in rows:
            values = {
                name: row[index]
                for name, index in variable_values.items()
            }

            try:
                result = evaluate_formula(formula, values)
            except FormulaError:
                continue

            details = [
                f"{VARIABLES[name]}: {values[name]} ₽"
                for name in VARIABLES
                if name in formula
            ]

            self.formula_example_label.setText(
                f"Пример для экземпляра №{row[7]}\n"
                + "\n".join(details)
                + f"\n\nКомиссия по формуле: {round(result)} ₽"
                + f"\nСохранённая комиссия: {row[6]} ₽"
            )
            return

        self.formula_example_label.setText(
            "Не удалось рассчитать пример. Проверьте формулу "
            "и наличие необходимых данных."
        )
