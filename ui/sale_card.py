from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QDateEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QMenu
)
from database.database import get_connection

class SaleCard(QWidget):

    def __init__(self, sale_id=None, edit_mode=False, main_window=None):
        super().__init__()

        self.main_window = main_window
        self.sale_id = sale_id
        self.edit_mode = edit_mode
        self.sale_completed = sale_id is not None
        self.selected_instance_ids = set()
        self.existing_item_values = {}
        self.pending_deleted_sale_item_ids = set()
        layout = QVBoxLayout()

        title = QLabel("Продажа")
        layout.addWidget(title)

        # Номер продажи
        number_layout = QHBoxLayout()

        number_layout.addWidget(
            QLabel("Номер продажи:")
        )

        self.number = QLabel("Новая")

        number_layout.addWidget(
            self.number
        )

        layout.addLayout(
            number_layout
        )

        # Дата
        date_layout = QHBoxLayout()

        date_layout.addWidget(
            QLabel("Дата продажи:")
        )

        self.sale_date = QDateEdit()
        self.sale_date.setDate(
            QDate.currentDate()
        )
        self.sale_date.setCalendarPopup(
            True
        )

        date_layout.addWidget(
            self.sale_date
        )

        layout.addLayout(
            date_layout
        )

        # Комментарий
        comment_layout = QHBoxLayout()

        comment_layout.addWidget(
            QLabel("Комментарий:")
        )

        self.comment = QLineEdit()

        comment_layout.addWidget(
            self.comment
        )

        layout.addLayout(
            comment_layout
        )

        self.items_layout = QVBoxLayout()

        layout.addLayout(
            self.items_layout
        )

        # Таблица экземпляров
        self.items_table = QTableWidget()

        self.items_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.items_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.items_table.setContextMenuPolicy(
            Qt.CustomContextMenu
        )

        self.items_table.customContextMenuRequested.connect(
            self.show_item_context_menu
        )
        self.items_table.setColumnCount(
            12
        )

        self.items_table.setHorizontalHeaderLabels([
            "№",
            "Производитель",
            "Артикул",
            "Название",
            "Штрихкод",
            "Закупка",
            "Закуп. доставка",
            "Цена продажи",
            "Доставка",
            "Упаковка",
            "Комиссия",
            "Прибыль"
        ])

        layout.addWidget(
            self.items_table
        )

        # Итоги
        self.total_label = QLabel(
            "Итого: продажа 0 ¥ | доставка 0 ¥ | "
            "упаковка 0 ¥ | комиссия 0 ¥ | прибыль 0 ¥"
        )

        layout.addWidget(
            self.total_label
        )

        # Кнопки
        self.add_item_button = QPushButton(
            "+ Добавить экземпляр"
        )

        self.complete_button = QPushButton(
            "Завершить продажу"
        )
        if self.edit_mode:
            self.complete_button.setText("Сохранить изменения")

        buttons_layout = QHBoxLayout()

        buttons_layout.addWidget(
            self.add_item_button
        )

        buttons_layout.addWidget(
            self.complete_button
        )
        layout.addLayout(
            buttons_layout
        )

        self.complete_button.clicked.connect(
            self.on_complete_button_clicked
        )
        self.add_item_button.clicked.connect(
            self.add_item
        )

        self.setLayout(
            layout
        )

        # Если открываем существующую продажу —
        # загружаем её данные.
        if self.sale_id is not None:
            self.load_sale()
        else:
            self.add_item_button.setEnabled(
                True
            )

    def load_sale(self):
        from models.sale import (
            get_sale,
            get_sale_items
        )

        sale = get_sale(
            self.sale_id
        )

        if sale is None:
            QMessageBox.warning(
                self,
                "Продажа",
                "Продажа не найдена."
            )
            return

        # Номер
        self.number.setText(
            f"№{sale[1]:05d}"
        )

        # Дата
        sale_date = QDate.fromString(
            sale[2],
            "yyyy-MM-dd"
        )

        if sale_date.isValid():
            self.sale_date.setDate(
                sale_date
            )

        # Комментарий
        self.comment.setText(
            sale[4] or ""
        )

        # Загружаем позиции
        items = get_sale_items(
            self.sale_id
        )

        for sale_item in items:
            self.add_existing_item(
                sale_item
            )

        if not self.edit_mode:
            # Режим просмотра
            self.sale_date.setEnabled(
                False
            )

            self.comment.setReadOnly(
                True
            )

            self.add_item_button.setEnabled(
                False
            )

            self.complete_button.setEnabled(
                False
            )
        else:
            # Режим редактирования
            self.sale_date.setEnabled(
                True
            )

            self.comment.setReadOnly(
                False
            )

            self.add_item_button.setEnabled(
                True
            )

            self.complete_button.setEnabled(
                True
            )

        self.update_totals()

    def add_existing_item(
        self,
        sale_item
    ):
        (
            sale_item_id,
            instance_id,
            product_id,
            internal_number,
            manufacturer,
            part_number,
            product_name,
            barcode,
            purchase_price,
            purchase_shipping,
            sale_price,
            buyer_shipping,
            packaging,
            commission,
            profit,
            active
        ) = sale_item

        row = self.items_table.rowCount()

        self.items_table.insertRow(
            row
        )

        self.items_table.setRowHeight(
            row,
            30
        )

        # Сохраняем исходные значения позиции.
        self.existing_item_values[row] = {
            "sale_item_id": sale_item_id,
            "product_id": product_id,
            "sale_price": sale_price or 0,
            "buyer_shipping": buyer_shipping or 0,
            "packaging": packaging or 0,
            "commission": commission or 0,
            "profit": profit or 0
        }

        # № экземпляра
        number_item = QTableWidgetItem(
            str(internal_number)
        )

        number_item.setData(
            Qt.UserRole,
            instance_id
        )

        self.items_table.setItem(
            row,
            0,
            number_item
        )

        # Производитель
        self.items_table.setItem(
            row,
            1,
            QTableWidgetItem(
                manufacturer or ""
            )
        )

        self.items_table.setItem(
            row,
            2,
            QTableWidgetItem(
                part_number or ""
            )
        )

        self.items_table.setItem(
            row,
            3,
            QTableWidgetItem(
                product_name or ""
            )
        )

        self.items_table.setItem(
            row,
            4,
            QTableWidgetItem(
                barcode or ""
            )
        )

        self.items_table.setItem(
            row,
            5,
            QTableWidgetItem(
                str(purchase_price or 0)
            )
        )

        self.items_table.setItem(
            row,
            6,
            QTableWidgetItem(
                str(purchase_shipping or 0)
            )
        )

        # Цена продажи
        sale_price_widget = QSpinBox()

        sale_price_widget.setRange(
            0,
            999999999
        )

        sale_price_widget.setSuffix(
            " ¥"
        )

        sale_price_widget.setValue(
            sale_price or 0
        )

        # В режиме просмотра поле заблокировано.
        sale_price_widget.setEnabled(
            self.edit_mode
        )

        self.items_table.setCellWidget(
            row,
            7,
            sale_price_widget
        )

        # Доставка покупателя
        buyer_shipping_widget = QSpinBox()

        buyer_shipping_widget.setRange(
            0,
            999999999
        )

        buyer_shipping_widget.setSuffix(
            " ¥"
        )

        buyer_shipping_widget.setValue(
            buyer_shipping or 0
        )

        buyer_shipping_widget.setEnabled(
            self.edit_mode
        )

        self.items_table.setCellWidget(
            row,
            8,
            buyer_shipping_widget
        )

        # Упаковка
        packaging_widget = QSpinBox()

        packaging_widget.setRange(
            0,
            999999999
        )

        packaging_widget.setSuffix(
            " ¥"
        )

        packaging_widget.setValue(
            packaging or 0
        )

        packaging_widget.setEnabled(
            self.edit_mode
        )

        self.items_table.setCellWidget(
            row,
            9,
            packaging_widget
        )

        # Комиссия
        commission_widget = QSpinBox()

        commission_widget.setRange(
            0,
            999999999
        )

        commission_widget.setSuffix(
            " ¥"
        )

        commission_widget.setValue(
            commission or 0
        )

        commission_widget.setEnabled(
            self.edit_mode
        )

        self.items_table.setCellWidget(
            row,
            10,
            commission_widget
        )

        # Обновление прибыли
        sale_price_widget.valueChanged.connect(
            lambda value,
            current_row=row:
            self.update_existing_item_profit(
                current_row
            )
        )

        buyer_shipping_widget.valueChanged.connect(
            lambda value,
            current_row=row:
            self.update_existing_item_profit(
                current_row
            )
        )

        packaging_widget.valueChanged.connect(
            lambda value,
            current_row=row:
            self.update_existing_item_profit(
                current_row
            )
        )

        commission_widget.valueChanged.connect(
            lambda value,
            current_row=row:
            self.update_existing_item_profit(
                current_row
            )
        )

        # Прибыль
        self.items_table.setItem(
            row,
            11,
            QTableWidgetItem(
                f"{profit or 0} ¥"
            )
        )

        if not active:
            for column in range(
                self.items_table.columnCount()
            ):
                item = self.items_table.item(
                    row,
                    column
                )

                if item is not None:
                    item.setForeground(
                        Qt.gray
                    )

            sale_price_widget.setEnabled(False)
            buyer_shipping_widget.setEnabled(False)
            packaging_widget.setEnabled(False)
            commission_widget.setEnabled(False)

    def create_sale(self):
        self.sale_started = True

        self.create_button.setEnabled(
            False
        )

        self.create_button.setText(
            "Продажа начата"
        )

        self.add_item_button.setEnabled(
            True
        )

    def add_item(self):
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QLineEdit,
            QPushButton
        )

        dialog = QDialog(self)

        layout = QVBoxLayout()

        search_input = QLineEdit()

        search_input.setPlaceholderText(
            "Штрихкод, артикул, название, № экземпляра..."
        )

        layout.addWidget(
            search_input
        )

        search_button = QPushButton(
            "Поиск"
        )

        layout.addWidget(
            search_button
        )

        results_layout = QVBoxLayout()

        layout.addLayout(
            results_layout
        )

        search_button.clicked.connect(
            lambda: self.search_instances(
                search_input.text(),
                dialog,
                results_layout
            )
        )

        dialog.setLayout(
            layout
        )

        dialog.setWindowTitle(
            "Добавить экземпляр"
        )

        dialog.exec()

    def search_instances(
        self,
        search_text,
        dialog,
        results_layout
    ):
        while results_layout.count():
            item = results_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        from models.instance import search_instances

        results = search_instances(
            search_text.strip()
        )

        for result in results:
            button = QPushButton(
                f"№{result[1]} | "
                f"{result[2] or ''} | "
                f"{result[3] or ''} | "
                f"{result[4]}"
            )

            button.clicked.connect(
                lambda checked=False,
                instance_id=result[0],
                internal_number=result[1],
                manufacturer=result[2],
                part_number=result[3],
                product_name=result[4],
                barcode=result[5],
                purchase_price=result[7],
                purchase_shipping=result[8],
                default_buyer_shipping=result[9],
                default_packaging=result[10],
                default_delivery_option_id=result[11],
                default_commission_type=result[12],
                default_commission_value=result[13]:
                self.select_instance(
                    instance_id,
                    internal_number,
                    manufacturer,
                    part_number,
                    product_name,
                    barcode,
                    purchase_price,
                    purchase_shipping,
                    default_buyer_shipping,
                    default_packaging,
                    default_delivery_option_id,
                    default_commission_type,
                    default_commission_value,
                    dialog
                )
            )

            results_layout.addWidget(
                button
            )
    def show_item_context_menu(self, position):
        item = self.items_table.itemAt(
            position
        )

        if item is None:
            return

        row = self.items_table.rowAt(
            position.y()
        )

        if row < 0:
            return

        menu = QMenu(self)
        open_product_action = menu.addAction(
            "Открыть карточку товара"
        )
        open_instance_action = menu.addAction(
            "Открыть карточку экземпляра"
        )
        delete_action = None

        if (
            self.edit_mode
            or (
                self.sale_id is None
                and not self.sale_completed
            )
        ):
            delete_action = menu.addAction(
                "Удалить из продажи"
            )

        action = menu.exec(
            self.items_table.viewport().mapToGlobal(
                position
            )
        )
        if action == open_instance_action:
            instance_id = self.items_table.item(
                row,
                0
            ).data(
                Qt.UserRole
            )

            if (
                instance_id is not None
                and self.main_window is not None
            ):
                self.main_window.open_instance_card(
                    instance_id
                )

            return
        if action == open_product_action:
            values = self.existing_item_values.get(row)

            if (
                values is not None
                and values.get("product_id") is not None
                and self.main_window is not None
            ):
                self.main_window.open_product_card(
                    values["product_id"]
                )

            return
        if delete_action is not None and action == delete_action:
            self.items_table.selectRow(
                row
            )

            if self.sale_id is not None:
                self.remove_existing_item()

            else:
                self.remove_selected_item()
    def remove_selected_item(self):
        row = self.items_table.currentRow()

        if row < 0:
            return

        instance_id = self.items_table.item(
            row,
            0
        ).data(
            Qt.UserRole
        )

        self.selected_instance_ids.discard(
            instance_id
        )

        answer = QMessageBox.question(
            self,
            "Удаление",
            "Удалить экземпляр из продажи?"
        )

        if answer != QMessageBox.Yes:
            return

        self.items_table.removeRow(
            row
        )

        self.update_totals()
    def remove_existing_item(self):
        row = self.items_table.currentRow()

        if row < 0:
            return

        values = self.existing_item_values.get(
            row
        )

        if values is None:
            return

        answer = QMessageBox.question(
            self,
            "Удаление",
            "Удалить экземпляр из продажи?"
        )

        if answer != QMessageBox.Yes:
            return

        sale_item_id = values["sale_item_id"]

        self.pending_deleted_sale_item_ids.add(
            sale_item_id
        )

        self.items_table.removeRow(
            row
        )

        # Перестраиваем соответствие строк и позиций продажи.
        new_values = {}

        for old_row, old_values in self.existing_item_values.items():
            if old_row == row:
                continue

            if old_row > row:
                new_row = old_row - 1
            else:
                new_row = old_row

            new_values[new_row] = old_values

        self.existing_item_values = new_values

        self.update_totals()
    def select_instance(
        self,
        instance_id,
        internal_number,
        manufacturer,
        part_number,
        product_name,
        barcode,
        purchase_price,
        purchase_shipping,
        default_buyer_shipping,
        default_packaging,
        default_delivery_option_id,
        default_commission_type,
        default_commission_value,
        dialog
    ):
        if hasattr(
            self,
            "selected_instance_ids"
        ):
            if instance_id in self.selected_instance_ids:
                return
        else:
            self.selected_instance_ids = set()

        self.selected_instance_ids.add(
            instance_id
        )

        self.commission_manual = False
        self.selected_instance_id = instance_id

        row = self.items_table.rowCount()

        self.items_table.insertRow(
            row
        )

        self.items_table.setRowHeight(
            row,
            30
        )

        self.items_table.setItem(
            row,
            0,
            QTableWidgetItem(
                str(internal_number)
            )
        )

        self.items_table.item(
            row,
            0
        ).setData(
            Qt.UserRole,
            instance_id
        )

        self.items_table.setItem(
            row,
            1,
            QTableWidgetItem(
                manufacturer or ""
            )
        )

        self.items_table.setItem(
            row,
            2,
            QTableWidgetItem(
                part_number or ""
            )
        )

        self.items_table.setItem(
            row,
            3,
            QTableWidgetItem(
                product_name
            )
        )

        self.items_table.setItem(
            row,
            4,
            QTableWidgetItem(
                barcode or ""
            )
        )

        self.items_table.setItem(
            row,
            5,
            QTableWidgetItem(
                str(purchase_price)
            )
        )

        self.items_table.setItem(
            row,
            6,
            QTableWidgetItem(
                str(purchase_shipping)
            )
        )

        sale_price = QSpinBox()

        sale_price.setRange(
            0,
            999999999
        )

        sale_price.setSuffix(
            " ¥"
        )

        self.items_table.setCellWidget(
            row,
            7,
            sale_price
        )
        delivery_shipping = None
        delivery_packaging = None

        if default_delivery_option_id is not None:
            connection = get_connection()

            try:
                cursor = connection.execute(
                    """
                    SELECT shipping_cost, packaging_cost
                    FROM delivery_options
                    WHERE id = ?
                    """,
                    (default_delivery_option_id,)
                )

                delivery_option = cursor.fetchone()

                if delivery_option is not None:
                    delivery_shipping = delivery_option[0]
                    delivery_packaging = delivery_option[1]

            finally:
                connection.close()

        if delivery_shipping is None:
            delivery_shipping = default_buyer_shipping

        if delivery_packaging is None:
            delivery_packaging = default_packaging
        buyer_shipping = QSpinBox()

        buyer_shipping.setRange(
            0,
            999999999
        )

        buyer_shipping.setSuffix(
            " ¥"
        )

        buyer_shipping.setValue(
            delivery_shipping or 0
        )

        self.items_table.setCellWidget(
            row,
            8,
            buyer_shipping
        )

        packaging = QSpinBox()

        packaging.setRange(
            0,
            999999999
        )

        packaging.setSuffix(
            " ¥"
        )

        packaging.setValue(
            delivery_packaging or 0
        )

        self.items_table.setCellWidget(
            row,
            9,
            packaging
        )

        commission = QSpinBox()

        commission.setProperty(
            "manual",
            False
        )

        commission.setRange(
            0,
            999999999
        )

        commission.setSuffix(
            " ¥"
        )

        self.items_table.setCellWidget(
            row,
            10,
            commission
        )

        commission.editingFinished.connect(
            lambda: setattr(
                self,
                "commission_manual",
                True
            )
        )

        def update_commission(value):
            if commission.property("manual"):
                return

            commission.setValue(
                round(
                    value * default_commission_value / 100
                )
                if default_commission_type == "percent"
                else int(
                    default_commission_value or 0
                )
            )

        sale_price.valueChanged.connect(
            update_commission
        )

        commission.editingFinished.connect(
            lambda: commission.setProperty(
                "manual",
                True
            )
        )

        sale_price.valueChanged.connect(
            lambda: (
                self.update_profit(
                    row,
                    sale_price,
                    buyer_shipping,
                    packaging,
                    commission,
                    purchase_price,
                    purchase_shipping
                ),
                self.update_totals()
            )
        )

        buyer_shipping.valueChanged.connect(
            lambda: (
                self.update_profit(
                    row,
                    sale_price,
                    buyer_shipping,
                    packaging,
                    commission,
                    purchase_price,
                    purchase_shipping
                ),
                self.update_totals()
            )
        )

        packaging.valueChanged.connect(
            lambda: (
                self.update_profit(
                    row,
                    sale_price,
                    buyer_shipping,
                    packaging,
                    commission,
                    purchase_price,
                    purchase_shipping
                ),
                self.update_totals()
            )
        )

        commission.valueChanged.connect(
            lambda: (
                self.update_profit(
                    row,
                    sale_price,
                    buyer_shipping,
                    packaging,
                    commission,
                    purchase_price,
                    purchase_shipping
                ),
                self.update_totals()
            )
        )

        self.update_profit(
            row,
            sale_price,
            buyer_shipping,
            packaging,
            commission,
            purchase_price,
            purchase_shipping
        )

        self.update_totals()

        dialog.accept()
    def update_existing_item_profit(
        self,
        row
    ):
        values = self.existing_item_values.get(
            row
        )

        if values is None:
            return

        sale_price_widget = self.items_table.cellWidget(
            row,
            7
        )

        buyer_shipping_widget = self.items_table.cellWidget(
            row,
            8
        )

        packaging_widget = self.items_table.cellWidget(
            row,
            9
        )

        commission_widget = self.items_table.cellWidget(
            row,
            10
        )

        if (
            sale_price_widget is None
            or buyer_shipping_widget is None
            or packaging_widget is None
            or commission_widget is None
        ):
            return

        current_sale_price = sale_price_widget.value()
        current_buyer_shipping = buyer_shipping_widget.value()
        current_packaging = packaging_widget.value()
        current_commission = commission_widget.value()

        # Прибыль корректируем относительно
        # уже сохранённой прибыли.
        #
        # Доставка покупателя не входит в прибыль:
        # она оплачивается покупателем и исключается
        # из суммы продажи.
        profit = (
            values["profit"]
            + (
                current_sale_price
                - values["sale_price"]
            )
            - (
                current_buyer_shipping
                - values["buyer_shipping"]
            )
            - (
                current_packaging
                - values["packaging"]
            )
            - (
                current_commission
                - values["commission"]
            )
        )

        self.items_table.setItem(
            row,
            11,
            QTableWidgetItem(
                f"{profit} ¥"
            )
        )

        self.update_totals()
    def update_profit(
        self,
        row,
        sale_price,
        buyer_shipping,
        packaging,
        commission,
        purchase_price,
        purchase_shipping
    ):
        profit = (
            sale_price.value()
            - buyer_shipping.value()
            - packaging.value()
            - commission.value()
            - purchase_price
            - purchase_shipping
        )

        self.items_table.setItem(
            row,
            11,
            QTableWidgetItem(
                str(profit)
            )
        )
    def on_complete_button_clicked(self):
        if self.edit_mode and self.sale_id is not None:
            self.save_sale_changes()
            return

        self.complete_sale()
    def save_sale_changes(self):
        from database.database import get_connection

        connection = get_connection()
        try:
            total_profit = 0

            for row in range(self.items_table.rowCount()):
                instance_id = self.items_table.item(
                    row, 0
                ).data(Qt.UserRole)

                sale_price = self.items_table.cellWidget(
                    row, 7
                ).value()

                buyer_shipping = self.items_table.cellWidget(
                    row, 8
                ).value()

                packaging = self.items_table.cellWidget(
                    row, 9
                ).value()

                commission = self.items_table.cellWidget(
                    row, 10
                ).value()

                result = connection.execute(
                    """
                    SELECT purchase_price, purchase_shipping
                    FROM instances
                    WHERE id = ?
                    """,
                    (instance_id,)
                ).fetchone()

                if result is None:
                    raise ValueError(
                        f"Экземпляр №{instance_id} не найден."
                    )

                purchase_price, purchase_shipping = result

                total_profit += (
                    sale_price
                    - buyer_shipping
                    - packaging
                    - commission
                    - (purchase_price or 0)
                    - (purchase_shipping or 0)
                )
        finally:
            connection.close()

        if total_profit < 0:
            answer = QMessageBox.question(
                self,
                "Продажа в убыток",
                (
                    f"После сохранения изменений общая прибыль "
                    f"составит {total_profit:.2f}.\n\n"
                    "Сохранить изменения и оставить продажу в убыток?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if answer != QMessageBox.Yes:
                return
        from models.sale import (
            update_sale,
            update_sale_item,
            remove_sale_item
        )

        sale_date = self.sale_date.date().toString(
            "yyyy-MM-dd"
        )

        comment = self.comment.text().strip()

        try:
            # Сохраняем дату и комментарий
            update_sale(
                self.sale_id,
                sale_date,
                comment
            )
            for sale_item_id in self.pending_deleted_sale_item_ids:
                remove_sale_item(
                    sale_item_id
                )
            # Сохраняем финансовые данные позиций
            for row in range(
                self.items_table.rowCount()
            ):
                values = self.existing_item_values.get(
                    row
                )

                if values is None:
                    instance_id = self.items_table.item(
                        row,
                        0
                    ).data(
                        Qt.UserRole
                    )

                    sale_price_widget = self.items_table.cellWidget(
                        row,
                        7
                    )
                    buyer_shipping_widget = self.items_table.cellWidget(
                        row,
                        8
                    )
                    packaging_widget = self.items_table.cellWidget(
                        row,
                        9
                    )
                    commission_widget = self.items_table.cellWidget(
                        row,
                        10
                    )

                    if (
                        instance_id is None
                        or sale_price_widget is None
                        or buyer_shipping_widget is None
                        or packaging_widget is None
                        or commission_widget is None
                    ):
                        continue

                    from models.sale import add_sale_item
                    print(
                        "ADD SALE ITEM:",
                        self.sale_id,
                        instance_id,
                        sale_price_widget.value()
                    )
                    add_sale_item(
                        self.sale_id,
                        instance_id,
                        sale_price_widget.value(),
                        buyer_shipping_widget.value(),
                        packaging_widget.value(),
                        commission_widget.value()
                    )

                    continue

                sale_item_id = values["sale_item_id"]

                sale_price_widget = self.items_table.cellWidget(
                    row,
                    7
                )

                buyer_shipping_widget = self.items_table.cellWidget(
                    row,
                    8
                )

                packaging_widget = self.items_table.cellWidget(
                    row,
                    9
                )

                commission_widget = self.items_table.cellWidget(
                    row,
                    10
                )

                if (
                    sale_price_widget is None
                    or buyer_shipping_widget is None
                    or packaging_widget is None
                    or commission_widget is None
                ):
                    continue

                update_sale_item(
                    sale_item_id,
                    sale_price_widget.value(),
                    buyer_shipping_widget.value(),
                    packaging_widget.value(),
                    commission_widget.value()
                )

            QMessageBox.information(
                self,
                "Сохранение",
                "Изменения сохранены."
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка",
                str(error)
            )
    def complete_sale(self):
        if self.sale_completed:
            return

        if self.items_table.rowCount() == 0:
            QMessageBox.warning(
                self,
                "Продажа",
                "Добавьте хотя бы один экземпляр."
            )
            return

        sale_date = self.sale_date.date().toString(
            "yyyy-MM-dd"
        )

        comment = self.comment.text().strip()

        items = []

        for row in range(
            self.items_table.rowCount()
        ):
            instance_id = self.items_table.item(
                row,
                0
            ).data(
                Qt.UserRole
            )

            sale_price = self.items_table.cellWidget(
                row,
                7
            ).value()

            buyer_shipping = self.items_table.cellWidget(
                row,
                8
            ).value()

            packaging = self.items_table.cellWidget(
                row,
                9
            ).value()

            commission = self.items_table.cellWidget(
                row,
                10
            ).value()

            items.append({
                "instance_id": instance_id,
                "sale_price": sale_price,
                "buyer_shipping": buyer_shipping,
                "packaging": packaging,
                "commission": commission
            })

        from models.sale import finalize_sale
        from database.database import get_connection

        connection = get_connection()
        try:
            total_profit = 0

            for item in items:
                cursor = connection.execute(
                    """
                    SELECT purchase_price, purchase_shipping
                    FROM instances
                    WHERE id = ?
                    """,
                    (item["instance_id"],)
                )
                result = cursor.fetchone()

                if result is None:
                    raise ValueError(
                        f"Экземпляр №{item['instance_id']} не найден."
                    )

                purchase_price, purchase_shipping = result

                profit = (
                    item["sale_price"]
                    - item["buyer_shipping"]
                    - item["packaging"]
                    - item["commission"]
                    - (purchase_price or 0)
                    - (purchase_shipping or 0)
                )

                total_profit += profit
        finally:
            connection.close()

        if total_profit < 0:
            answer = QMessageBox.question(
                self,
                "Продажа в убыток",
                (
                    f"Общая прибыль по продаже составит "
                    f"{total_profit:.2f}, то есть будет получен убыток.\n\n"
                    "Всё равно завершить продажу?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if answer != QMessageBox.Yes:
                return

        try:
            sale_id, sale_number = finalize_sale(
                sale_date,
                comment,
                items
            )

            QMessageBox.information(
                self,
                "Продажа",
                f"Продажа №{sale_number} завершена."
            )

            self.sale_completed = True

            self.complete_button.setEnabled(
                False
            )

            self.add_item_button.setEnabled(
                False
            )

            self.sale_date.setEnabled(
                False
            )

            self.comment.setReadOnly(
                True
            )

            for row in range(
                self.items_table.rowCount()
            ):
                for column in range(
                    7,
                    11
                ):
                    widget = self.items_table.cellWidget(
                        row,
                        column
                    )

                    if widget is not None:
                        widget.setEnabled(
                            False
                        )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка",
                str(error)
            )

    def update_totals(self):
        total_sale = 0
        total_shipping = 0
        total_packaging = 0
        total_commission = 0
        total_profit = 0

        if self.items_table.rowCount() == 0:
            self.total_label.setText(
                "Итого: продажа 0 ¥ | доставка 0 ¥ | "
                "упаковка 0 ¥ | комиссия 0 ¥ | прибыль 0 ¥"
            )
            return

        for row in range(
            self.items_table.rowCount()
        ):
            # Для существующей продажи значения являются
            # обычными QTableWidgetItem.
            sale_widget = self.items_table.cellWidget(
                row,
                7
            )

            shipping_widget = self.items_table.cellWidget(
                row,
                8
            )

            packaging_widget = self.items_table.cellWidget(
                row,
                9
            )

            commission_widget = self.items_table.cellWidget(
                row,
                10
            )

            if sale_widget is not None:
                total_sale += sale_widget.value()
            else:
                total_sale += self._item_number(
                    row,
                    7
                )

            if shipping_widget is not None:
                total_shipping += shipping_widget.value()
            else:
                total_shipping += self._item_number(
                    row,
                    8
                )

            if packaging_widget is not None:
                total_packaging += packaging_widget.value()
            else:
                total_packaging += self._item_number(
                    row,
                    9
                )

            if commission_widget is not None:
                total_commission += commission_widget.value()
            else:
                total_commission += self._item_number(
                    row,
                    10
                )

            profit_item = self.items_table.item(
                row,
                11
            )

            if profit_item is not None:
                total_profit += self._item_number(
                    row,
                    11
                )

        self.total_label.setText(
            f"Итого: продажа {total_sale} ¥ | "
            f"доставка {total_shipping} ¥ | "
            f"упаковка {total_packaging} ¥ | "
            f"комиссия {total_commission} ¥ | "
            f"прибыль {total_profit} ¥"
        )

    def _item_number(self, row, column):
        item = self.items_table.item(
            row,
            column
        )

        if item is None:
            return 0

        text = item.text().replace(
            "¥",
            ""
        ).strip()

        try:
            return int(text)
        except ValueError:
            return 0