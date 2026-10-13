from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QMenu,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QPushButton,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
)

from database.database import get_connection


class InstanceCard(QWidget):
    def __init__(self, instance_id):
        super().__init__()

        self.instance_id = instance_id
        self.product_id = None

        main_layout = QVBoxLayout(self)

        title = QLabel("Экземпляр товара")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        main_layout.addWidget(title)

        form_layout = QFormLayout()

        self.internal_number = QLineEdit()
        self.internal_number.setReadOnly(True)

        self.product_name = QLineEdit()
        self.product_name.setReadOnly(True)

        self.condition = QComboBox()
        self.condition.addItem("Новый", "new")
        self.condition.addItem("Б/у", "used")
        self.condition.addItem("Неисправен", "defective")
        self.condition.addItem("На запчасти", "parts")

        self.purchase_price = QSpinBox()
        self.purchase_price.setRange(0, 100000000)
        self.purchase_price.setSuffix(" ¥")

        self.purchase_shipping = QSpinBox()
        self.purchase_shipping.setRange(0, 100000000)
        self.purchase_shipping.setSuffix(" ¥")

        self.purchase_cost = QSpinBox()
        self.purchase_cost.setRange(0, 100000000)
        self.purchase_cost.setSuffix(" ¥")
        self.purchase_cost.setReadOnly(True)

        self.purchase_price.valueChanged.connect(
            self.update_purchase_cost
        )

        self.purchase_shipping.valueChanged.connect(
            self.update_purchase_cost
        )

        self.update_purchase_cost()

        self.purchase_date = QLineEdit()
        self.listed_date = QLineEdit()
        self.listed_date.setReadOnly(False)
        self.status = QLineEdit()
        self.status.setReadOnly(True)
        self.listed_button = QPushButton("В продажу")

        self.listed_button.clicked.connect(
            self.toggle_listed
        )
        self.notes = QLineEdit()

        form_layout.addRow(
            "Внутренний номер:",
            self.internal_number
        )

        form_layout.addRow(
            "Товар:",
            self.product_name
        )

        form_layout.addRow(
            "Состояние:",
            self.condition
        )

        form_layout.addRow(
            "Цена закупки:",
            self.purchase_price
        )

        form_layout.addRow(
            "Доставка закупки:",
            self.purchase_shipping
        )
        form_layout.addRow(
            "Дата выставления:",
            self.listed_date
        )
        form_layout.addRow(
            "",
            self.listed_button
        )
        form_layout.addRow("Себестоимость:", self.purchase_cost)

        form_layout.addRow(
            "Дата закупки:",
            self.purchase_date
        )

        form_layout.addRow(
            "Статус:",
            self.status
        )

        form_layout.addRow(
            "Примечание:",
            self.notes
        )

        main_layout.addLayout(form_layout)

        history_label = QLabel("История")
        history_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        main_layout.addWidget(
            history_label
        )

        self.history_list = QListWidget()
        self.history_list.installEventFilter(self)
        self.history_list.setContextMenuPolicy(
            Qt.CustomContextMenu
        )

        self.history_list.customContextMenuRequested.connect(
            self.show_history_context_menu
        )
        self.history_list.setSelectionMode(
            QListWidget.SingleSelection
        )

        self.history_list.setMinimumHeight(
            120
        )

        self.history_list.setMaximumHeight(
            180
        )

        main_layout.addWidget(
            self.history_list
        )

        buttons_layout = QHBoxLayout()

        self.save_button = QPushButton(
            "Сохранить"
        )

        self.product_button = QPushButton(
            "К товару"
        )

        self.save_button.clicked.connect(
            self.save
        )

        self.product_button.clicked.connect(
            self.open_product_card
        )

        buttons_layout.addWidget(
            self.save_button
        )

        buttons_layout.addWidget(
            self.product_button
        )

        main_layout.addLayout(
            buttons_layout
        )

        main_layout.addStretch()

        self.load_instance()

    def load_instance(self):
        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT
                    instances.internal_number,
                    instances.product_id,
                    instances.condition,
                    instances.purchase_price,
                    instances.purchase_shipping,
                    instances.purchase_date,
                    instances.status,
                    instances.listed_date,
                    instances.notes,
                    products.name
                FROM instances
                JOIN products
                    ON products.id = instances.product_id
                WHERE instances.id = ?
                """,
                (self.instance_id,)
            )

            instance = cursor.fetchone()

        finally:
            connection.close()

        if instance is None:
            return
        self.product_id = instance[1]
        self.internal_number.setText(
            str(instance[0])
        )

        self.product_name.setText(
            instance[9] or ""
        )

        condition_index = self.condition.findData(
            instance[2]
        )

        if condition_index >= 0:
            self.condition.setCurrentIndex(
                condition_index
            )

        self.purchase_price.setValue(
            instance[3] or 0
        )

        self.purchase_shipping.setValue(
            instance[4] or 0
        )

        self.purchase_date.setText(
            instance[5] or ""
        )
        self.listed_date.setText(
            instance[7] or ""
        )

        if instance[7]:
            self.listed_button.setText(
                "Снять с продажи"
            )
        else:
            self.listed_button.setText(
                "В продажу"
            )
        status_names = {
            "in_stock": "В наличии",
            "sold": "Продан",
            "written_off": "Списан"
        }

        self.status.setText(
            status_names.get(
                instance[6],
                instance[6]
            )
        )

        if instance[6] in ("sold", "written_off"):
            self.condition.setEnabled(False)
        else:
            self.condition.setEnabled(True)
        if instance[6] == "sold":
            self.listed_button.setEnabled(False)
            self.listed_button.setText("Продан")

        elif instance[6] == "written_off":
            self.listed_button.setEnabled(False)
            self.listed_button.setText("Списан")

        else:
            self.listed_button.setEnabled(True)
        self.notes.setText(
            instance[8] or ""
        )
        self.load_history()
    def eventFilter(self, obj, event):
        if (
            obj is self.history_list
            and event.type() == event.Type.KeyPress
            and event.key() == Qt.Key_C
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            item = self.history_list.currentItem()

            if item is None:
                return True

            row_widget = self.history_list.itemWidget(item)

            if row_widget is not None:
                labels = row_widget.findChildren(QLabel)
                values = [label.text() for label in labels]
                QApplication.clipboard().setText("\t".join(values))

            return True

        return super().eventFilter(obj, event)
    def save(self):
        from database.database import get_connection

        condition = self.condition.currentData()
        purchase_price = self.purchase_price.value()
        purchase_shipping = self.purchase_shipping.value()
        purchase_date = self.purchase_date.text().strip()
        notes = self.notes.text().strip()

        connection = get_connection()

        try:
            connection.execute(
                """
                UPDATE instances
                SET
                    condition = ?,
                    purchase_price = ?,
                    purchase_shipping = ?,
                    purchase_date = ?,
                    notes = ?
                WHERE id = ?
                """,
                (
                    condition,
                    purchase_price,
                    purchase_shipping,
                    purchase_date,
                    notes,
                    self.instance_id
                )
            )

            connection.commit()

        except Exception as error:
            connection.rollback()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить экземпляр:\n\n{error}"
            )
            return

        finally:
            connection.close()

        QMessageBox.information(
            self,
            "Сохранено",
            "Экземпляр успешно сохранён."
        )

    def open_product_card(self):
        if self.product_id is None:
            return

        window = self.window()

        if hasattr(window, "open_product_card"):
            window.open_product_card(
                self.product_id
            )

    def toggle_listed(self):
        from datetime import date
        from database.database import get_connection

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT listed_date
                FROM instances
                WHERE id = ?
                """,
                (self.instance_id,)
            )

            result = cursor.fetchone()

            if result is None:
                return

            listed_date = result[0]

            if listed_date:
                new_date = None
            else:
                new_date = date.today().isoformat()

            connection.execute(
                """
                UPDATE instances
                SET listed_date = ?
                WHERE id = ?
                """,
                (
                    new_date,
                    self.instance_id
                )
            )
            if new_date:
                connection.execute(
                    """
                    INSERT INTO events (
                        event_date,
                        event_type,
                        instance_id,
                        product_id
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        new_date,
                        "listed",
                        self.instance_id,
                        self.product_id
                    )
                )
            connection.commit()

        except Exception as error:
            connection.rollback()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось изменить статус выставления:\n\n{error}"
            )
            return

        finally:
            connection.close()

        self.listed_date.setText(
            new_date or ""
        )

        if new_date:
            self.listed_button.setText(
                "Снять с продажи"
            )
        else:
            self.listed_button.setText(
                "В продажу"
            )

    def update_purchase_cost(self):
        purchase_price = self.purchase_price.value()
        purchase_shipping = self.purchase_shipping.value()

        self.purchase_cost.setValue(
            purchase_price + purchase_shipping
        )

    def show_history_context_menu(self, position):
        item = self.history_list.itemAt(position)

        if item is None:
            return

        event_type = item.data(
            Qt.UserRole
        )

        purchase_id = item.data(
            Qt.UserRole + 1
        )

        sale_id = item.data(
            Qt.UserRole + 2
        )

        menu = QMenu(self)

        if event_type == "purchase" and purchase_id:
            open_purchase_action = menu.addAction(
                "Открыть закупку"
            )

            open_purchase_action.triggered.connect(
                lambda: self.window().open_purchase(
                    purchase_id
                )
            )

        elif event_type == "sale" and sale_id:
            open_sale_action = menu.addAction(
                "Открыть продажу"
            )

            open_sale_action.triggered.connect(
                lambda: self.window().open_sale(
                    sale_id
                )
            )

        else:
            return

        menu.exec(
            self.history_list.mapToGlobal(position)
        )

    def load_history(self):
        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT
                    event_date,
                    event_type,
                    comment,
                    purchase_id,
                    sale_id
                FROM events
                WHERE instance_id = ?
                ORDER BY event_date, id
                """,
                (self.instance_id,)
            )

            events = cursor.fetchall()

        finally:
            connection.close()

        event_names = {
            "purchase": "Закупка",
            "listed": "Поступил в продажу",
            "sale": "Продажа",
            "return": "Возврат",
            "write_off": "Списание"
        }

        self.history_list.clear()

        for event in events:
            event_date = event[0] or ""
            event_type = event_names.get(
                event[1],
                event[1]
            )
            comment = event[2] or ""
            purchase_id = event[3]
            sale_id = event[4]
            item = QListWidgetItem()
            item.setData(
                Qt.UserRole,
                event[1]
            )

            item.setData(
                Qt.UserRole + 1,
                purchase_id
            )

            item.setData(
                Qt.UserRole + 2,
                sale_id
            )
            row_widget = QWidget()

            row_layout = QHBoxLayout(
                row_widget
            )

            row_layout.setContentsMargins(
                4, 2, 4, 2
            )

            date_label = QLabel(
                event_date
            )

            date_label.setFixedWidth(
                100
            )

            operation_label = QLabel(
                event_type
            )

            operation_label.setFixedWidth(
                180
            )

            comment_label = QLabel(
                comment
            )

            row_layout.addWidget(
                date_label
            )

            row_layout.addWidget(
                operation_label
            )

            row_layout.addWidget(
                comment_label
            )

            row_layout.addStretch()

            item.setSizeHint(
                row_widget.sizeHint()
            )

            self.history_list.addItem(
                item
            )

            self.history_list.setItemWidget(
                item,
                row_widget
            )