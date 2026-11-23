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
    QDateEdit,
    QCalendarWidget,
)

from database.database import get_connection
from ui.context_menus import (
    add_open_purchase_by_id_action,
    add_open_sale_by_id_action,
)
class NullableDateEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setReadOnly(True)
        self.setPlaceholderText("Выберите дату")
        self.calendar = QCalendarWidget(self)
        self.calendar.setWindowFlags(
            Qt.Popup
        )

        self.calendar.clicked.connect(
            self.set_selected_date
        )

    def set_selected_date(self, date):
        self.setText(
            date.toString("yyyy-MM-dd")
        )
        self.calendar.hide()

    def mousePressEvent(self, event):
        self.calendar.setSelectedDate(
            QDate.currentDate()
        ) if not self.text() else None

        self.calendar.move(
            self.mapToGlobal(self.rect().bottomLeft())
        )
        self.calendar.show()

    def setDate(self, date):
        self.setText(
            "" if not date.isValid()
            else date.toString("yyyy-MM-dd")
        )

    def date(self):
        return QDate.fromString(
            self.text(), "yyyy-MM-dd"
        )
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
        self.purchase_price.setSpecialValueText(" ")

        self.purchase_shipping = QSpinBox()
        self.purchase_shipping.setRange(0, 100000000)
        self.purchase_shipping.setSpecialValueText(" ")

        self.purchase_cost = QSpinBox()
        self.purchase_cost.setRange(0, 100000000)
        self.purchase_cost.setSpecialValueText(" ")
        self.purchase_cost.setReadOnly(True)

        self.purchase_price.valueChanged.connect(
            self.update_purchase_cost
        )

        self.purchase_shipping.valueChanged.connect(
            self.update_purchase_cost
        )

        self.update_purchase_cost()

        self.purchase_date = QLineEdit()
        self.listed_date = NullableDateEdit()

        form_layout.addRow(
            "Дата выставления:",
            self.listed_date
        )
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

        self.history_list.setMinimumHeight(120)
        self.history_list.setMaximumHeight(16777215)

        main_layout.addWidget(
            self.history_list,
            1
        )

        buttons_layout = QHBoxLayout()

        self.save_button = QPushButton(
            "Сохранить"
        )

        self.save_close_button = QPushButton(
            "Сохранить и закрыть"
        )

        self.product_button = QPushButton(
            "К товару"
        )

        self.save_button.clicked.connect(
            self.save
        )

        self.save_close_button.clicked.connect(
            self.save_and_close
        )

        self.product_button.clicked.connect(
            self.open_product_card
        )

        buttons_layout.addWidget(
            self.product_button
        )

        buttons_layout.addStretch()

        buttons_layout.addWidget(
            self.save_button
        )

        buttons_layout.addWidget(
            self.save_close_button
        )

        main_layout.addLayout(
            buttons_layout
        )

        main_layout.addStretch()

        self.load_instance()

    def get_form_state(self):
        return (
            self.condition.currentData(),
            self.purchase_price.value(),
            self.purchase_shipping.value(),
            self.purchase_date.text(),
            self.listed_date.text(),
            self.notes.text(),
        )

    def has_unsaved_changes(self):
        return (
            self.get_form_state()
            != getattr(self, "_saved_form_state", None)
        )

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
                    products.name,
                    products.manufacturer,
                    products.part_number
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

        product_name = "	".join(
            part for part in (
                instance[10],
                instance[11],
                instance[9]
            ) if part
        )

        self.product_name.setText(
            product_name
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
        listed_date = instance[7]

        if listed_date:
            self.listed_date.setDate(
                QDate.fromString(listed_date, "yyyy-MM-dd")
            )
        else:
            self.listed_date.clear()

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
        self._saved_form_state = self.get_form_state()
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
    def save_and_close(self):
        if not self.save():
            return

        window = self.window()

        if hasattr(window, "tabs") and hasattr(window, "close_tab"):
            index = window.tabs.indexOf(self)

            if index >= 0:
                window.close_tab(index)
                return

        self.close()

    def save(self):
        from database.database import get_connection

        condition = self.condition.currentData()
        purchase_price = self.purchase_price.value()
        purchase_shipping = self.purchase_shipping.value()
        purchase_date = self.purchase_date.text().strip()
        listed_date = self.listed_date.text().strip()
        notes = self.notes.text().strip()

        connection = get_connection()

        try:
            # Проверяем, выставлен ли экземпляр на продажу сейчас
            current = connection.execute(
                """
                SELECT listed_date
                FROM instances
                WHERE id = ?
                """,
                (self.instance_id,)
            ).fetchone()

            if current is None:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Экземпляр не найден."
                )
                return False

            # Если экземпляр снят с продажи, не сохраняем новую дату
            if not current[0]:
                listed_date = ""

            connection.execute(
                """
                UPDATE instances
                SET
                    condition = ?,
                    purchase_price = ?,
                    purchase_shipping = ?,
                    purchase_date = ?,
                    listed_date = ?,
                    notes = ?
                WHERE id = ?
                """,
                (
                    condition,
                    purchase_price,
                    purchase_shipping,
                    purchase_date,
                    listed_date or None,
                    notes,
                    self.instance_id
                )
            )

            # Меняем дату существующего события, не создавая повторных
            if listed_date:
                cursor = connection.execute(
                    """
                    UPDATE events
                    SET event_date = ?
                    WHERE id = (
                        SELECT id
                        FROM events
                        WHERE instance_id = ?
                          AND event_type = 'listed'
                        ORDER BY id DESC
                        LIMIT 1
                    )
                    """,
                    (listed_date, self.instance_id)
                )

                if cursor.rowcount == 0:
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
                            listed_date,
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
                f"Не удалось сохранить экземпляр:\n\n{error}"
            )
            return False

        finally:
            connection.close()

        self.load_instance()
        self.load_history()

        QMessageBox.information(
            self,
            "Сохранено",
            "Экземпляр успешно сохранён."
        )
        return True

    def open_product_card(self):
        if self.product_id is None:
            return True

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
                event_type = "listed"
                event_date = new_date
                comment = None
            else:
                from datetime import date

                event_type = "unlisted"
                event_date = date.today().isoformat()
                comment = None

            connection.execute(
                """
                INSERT INTO events (
                    event_date,
                    event_type,
                    instance_id,
                    product_id,
                    comment
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_date,
                    event_type,
                    self.instance_id,
                    self.product_id,
                    comment
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

        if new_date:
            self.listed_date.setDate(
                QDate.fromString(new_date, "yyyy-MM-dd")
            )
        else:
            self.listed_date.clear()

        self.load_instance()

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

        event_type = item.data(Qt.UserRole)
        purchase_id = item.data(Qt.UserRole + 1)
        sale_id = item.data(Qt.UserRole + 2)

        menu = QMenu(self)
        main_window = self.window()

        if event_type == "purchase" and purchase_id:
            add_open_purchase_by_id_action(
                menu,
                main_window,
                purchase_id
            )

        elif event_type == "sale" and sale_id:
            add_open_sale_by_id_action(
                menu,
                main_window,
                sale_id
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
            "unlisted": "Снят с продажи",
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