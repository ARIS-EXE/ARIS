from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QDateEdit,
    QPushButton,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMenu,
    QDialog
)
from pathlib import Path
from PySide6.QtGui import QPixmap

from app_paths import IMAGE_DIR
from PySide6.QtCore import QDate, Qt
from database.database import get_connection
from models.purchase import (
    create_purchase_multi,
    get_unlinked_instances,
)

class PurchaseCard(QWidget):

    def __init__(self, main_window, purchase_id=None):
        super().__init__()

        self.main_window = main_window
        self.purchase_saved = False
        self.purchase_id = purchase_id

        layout = QVBoxLayout()

        # ============================================================
        # Товары в закупке
        # ============================================================

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(2)

        self.items_table.setHorizontalHeaderLabels([
            "Товар",
            "Количество"
        ])

        self.items_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch
        )

        self.items_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents
        )

        # Поля таблицы только для просмотра
        self.items_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.items_table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.items_table.customContextMenuRequested.connect(
            self.show_context_menu
        )

        layout.addWidget(
            self.items_table
        )

        # ============================================================
        # Основная рабочая область
        # ============================================================

        main_area = QHBoxLayout()

        # ------------------------------------------------------------
        # Левая часть — примерно 2/3 окна
        # ------------------------------------------------------------

        left_area = QVBoxLayout()

        # Дата + стоимость + доставка
        info_layout = QHBoxLayout()

        info_layout.addWidget(
            QLabel("Дата закупки:")
        )

        self.purchase_date = QDateEdit()
        self.purchase_date.setDate(
            QDate.currentDate()
        )
        self.purchase_date.setCalendarPopup(
            True
        )

        info_layout.addWidget(
            self.purchase_date
        )

        info_layout.addWidget(
            QLabel("Стоимость товара:")
        )

        self.total_purchase_price = QSpinBox()
        self.total_purchase_price.setRange(
            0,
            100_000_000
        )
        self.total_purchase_price.setSuffix(
            " ¥"
        )

        info_layout.addWidget(
            self.total_purchase_price
        )

        info_layout.addWidget(
            QLabel("Доставка:")
        )

        self.total_shipping = QSpinBox()
        self.total_shipping.setRange(
            0,
            100_000_000
        )
        self.total_shipping.setSuffix(
            " ¥"
        )

        info_layout.addWidget(
            self.total_shipping
        )

        left_area.addLayout(
            info_layout
        )

        # ------------------------------------------------------------
        # Поиск товара
        # ------------------------------------------------------------

        self.product_search = QLineEdit()

        self.product_search.setPlaceholderText(
            "Поиск товара..."
        )

        self.product_search.textChanged.connect(
            self.update_product_list
        )

        left_area.addWidget(
            self.product_search
        )

        # ------------------------------------------------------------
        # Результаты поиска
        # ------------------------------------------------------------

        self.product_list = QListWidget()
        self.product_list.doubleClicked.connect(
            self.add_product_from_double_click
        )
        self.product_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.product_list.customContextMenuRequested.connect(
            self.show_product_list_context_menu
        )
        self.product_list.currentItemChanged.connect(
            self.update_product_image
        )
        left_area.addWidget(
            self.product_list
        )

        # ------------------------------------------------------------
        # Количество + добавление
        # ------------------------------------------------------------

        add_layout = QHBoxLayout()
        add_layout.setAlignment(Qt.AlignTop)
        self.new_product_button = QPushButton(
            "+ Новый товар"
        )

        self.new_product_button.setFixedWidth(
            180
        )

        self.new_product_button.clicked.connect(
            self.main_window.open_new_product
        )

        add_layout.addWidget(
            self.new_product_button,
            alignment=Qt.AlignTop
        )

        add_layout.addWidget(
            QLabel("Количество:"),
            alignment=Qt.AlignTop
        )

        self.count = QSpinBox()
        self.count.setRange(
            1,
            10000
        )

        add_layout.addWidget(
            self.count,
            alignment=Qt.AlignTop
        )

        # Вертикальный блок кнопок добавления
        buttons_layout = QVBoxLayout()

        self.add_button = QPushButton(
            "Добавить товар"
        )

        self.add_button.clicked.connect(
            self.add_product
        )

        self.add_existing_instance_button = QPushButton(
            "Добавить существующий экземпляр"
        )

        self.add_existing_instance_button.clicked.connect(
            self.add_existing_instance
        )

        buttons_layout.addWidget(
            self.add_button
        )

        buttons_layout.addWidget(
            self.add_existing_instance_button
        )

        add_layout.addLayout(
            buttons_layout
        )

        left_area.addLayout(
            add_layout
        )

        # ------------------------------------------------------------
        # Сохранение
        # ------------------------------------------------------------

        self.save_button = QPushButton(
            "Сохранить закупку"
        )

        self.save_button.clicked.connect(
            self.save_purchase
        )

        add_layout.addWidget(
            self.save_button,
            alignment=Qt.AlignTop
        )

        main_area.addLayout(
            left_area,
            2
        )

        # ============================================================
        # Правая часть — фото товара
        # ============================================================

        self.product_image = QLabel()
        self.product_image_pixmap = QPixmap()
        self.product_image.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.product_image.setText(
            "Фото товара"
        )

        self.product_image.setMinimumWidth(
            200
        )

        main_area.addWidget(
            self.product_image,
            1
        )

        # ============================================================
        # Добавляем рабочую область
        # ============================================================

        layout.addLayout(
            main_area
        )

        # ============================================================
        # Загрузка товаров
        # ============================================================

        self.load_products()
        self.setLayout(layout)

        if self.purchase_id is not None:
            self.load_purchase(self.purchase_id)
    def load_products(self):
        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT
                    id,
                    barcode,
                    manufacturer,
                    part_number,
                    name,
                    image_path
                FROM products
                WHERE deleted = 0
                ORDER BY manufacturer, name
                """
            )

            products = cursor.fetchall()

        finally:
            connection.close()

        self.all_products = products

        self.update_product_list()
    def update_product_list(self):
        search_text = (
            self.product_search.text()
            .strip()
            .lower()
        )

        self.product_list.clear()

        # Пока ничего не ищем — список пустой
        if not search_text:
            return

        search_words = search_text.split()

        for product in self.all_products:
            product_id = product[0]
            barcode = product[1] or ""
            manufacturer = product[2] or ""
            part_number = product[3] or ""
            name = product[4] or ""
            image_path = product[5] or ""

            search_fields = [
                barcode.lower(),
                manufacturer.lower(),
                part_number.lower(),
                name.lower()
            ]

            # Каждое введённое слово должно
            # найтись хотя бы в одном из полей
            if not all(
                any(
                    word in field
                    for field in search_fields
                )
                for word in search_words
            ):
                continue

            text = " | ".join(
                part
                for part in [
                    manufacturer,
                    part_number,
                    name
                ]
                if part
            )

            if barcode:
                text = f"{text} | ШК: {barcode}"

            item = QListWidgetItem(text)

            item.setData(
                1000,
                product_id
            )
            item.setData(
                1001,
                image_path
            )
            self.product_list.addItem(item)
    def update_product_image(self, current, previous):
        if current is None:
            self.product_image_pixmap = QPixmap()

            self.product_image.clear()
            self.product_image.setText(
                "Фото товара"
            )
            return

        image_filename = current.data(
            1001
        )

        if not image_filename:
            self.product_image_pixmap = QPixmap()

            self.product_image.clear()
            self.product_image.setText(
                "Фото отсутствует"
            )
            return

        image_path = IMAGE_DIR / image_filename

        if not image_path.exists():
            self.product_image_pixmap = QPixmap()

            self.product_image.clear()
            self.product_image.setText(
                "Фото отсутствует"
            )
            return

        pixmap = QPixmap(
            str(image_path)
        )

        if pixmap.isNull():
            self.product_image_pixmap = QPixmap()

            self.product_image.clear()
            self.product_image.setText(
                "Фото отсутствует"
            )
            return

        self.product_image_pixmap = pixmap

        self.update_product_image_size()
    def update_product_image_size(self):
        if self.product_image_pixmap.isNull():
            return

        scaled_pixmap = self.product_image_pixmap.scaled(
            self.product_image.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.product_image.setPixmap(
            scaled_pixmap
        )
    def resizeEvent(self, event):
        super().resizeEvent(event)

        self.update_product_image_size()
    def add_product_from_double_click(self, index):
        self.add_product()
    def add_product(self):
        selected_item = self.product_list.currentItem()

        if selected_item is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Выберите товар."
            )
            return

        product_id = selected_item.data(1000)
        product_text = selected_item.text()

        count = self.count.value()

        # Проверяем, есть ли этот товар уже в таблице
        for row in range(
            self.items_table.rowCount()
        ):
            product_item = self.items_table.item(
                row,
                0
            )

            count_item = self.items_table.item(
                row,
                1
            )

            if product_item is None:
                continue

            existing_product_id = product_item.data(
                1000
            )

            if existing_product_id == product_id:
                current_count = int(
                    count_item.text()
                )

                count_item.setText(
                    str(current_count + count)
                )

                return

        # Если товара ещё нет — добавляем новую строку
        row = self.items_table.rowCount()

        self.items_table.insertRow(
            row
        )

        product_item = QTableWidgetItem(
            product_text
        )

        product_item.setData(
            1000,
            product_id
        )

        count_item = QTableWidgetItem(
            str(count)
        )

        self.items_table.setItem(
            row,
            0,
            product_item
        )

        self.items_table.setItem(
            row,
            1,
            count_item
        )

    def add_instance_to_purchase(self, instance_id):
        from models.instance import get_instance

        instance = get_instance(instance_id)

        if instance is None or instance[9]:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Экземпляр не найден или удалён."
            )
            return

        for row in range(self.items_table.rowCount()):
            product_item = self.items_table.item(row, 0)

            if (
                product_item is not None
                and product_item.data(Qt.UserRole + 1) == instance_id
            ):
                QMessageBox.information(
                    self,
                    "Уже добавлен",
                    "Этот экземпляр уже добавлен в закупку."
                )
                return

        internal_number = instance[1]
        product_id = instance[2]

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT manufacturer, part_number, name
                FROM products
                WHERE id = ? AND deleted = 0
                """,
                (product_id,)
            )
            product = cursor.fetchone()
        finally:
            connection.close()

        if product is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось найти товар этого экземпляра."
            )
            return

        product_name = " ".join(
            str(value)
            for value in product
            if value is not None and str(value).strip()
        )

        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        product_item = QTableWidgetItem(
            f"Экземпляр № {internal_number} — {product_name}"
        )
        product_item.setData(Qt.UserRole + 1, instance_id)
        product_item.setData(Qt.UserRole, None)

        count_item = QTableWidgetItem("1")

        self.items_table.setItem(row, 0, product_item)
        self.items_table.setItem(row, 1, count_item)

    def add_existing_instance(self):
        instances = get_unlinked_instances()

        if not instances:
            QMessageBox.information(
                self,
                "Нет экземпляров",
                "Нет экземпляров, не включённых в другие закупки."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Выбрать существующий экземпляр")
        dialog.resize(600, 400)

        dialog_layout = QVBoxLayout(dialog)

        instance_list = QListWidget(dialog)

        for instance in instances:
            (
                instance_id,
                internal_number,
                manufacturer,
                part_number,
                name,
            ) = instance

            product_name = " ".join(
                str(value)
                for value in (
                    manufacturer,
                    part_number,
                    name,
                )
                if value
            )

            item = QListWidgetItem(
                f"№ {internal_number} — {product_name}"
            )

            item.setData(Qt.UserRole, instance_id)
            instance_list.addItem(item)

        dialog_layout.addWidget(instance_list)

        buttons_layout = QHBoxLayout()

        select_button = QPushButton("Выбрать")
        cancel_button = QPushButton("Отмена")

        buttons_layout.addWidget(select_button)
        buttons_layout.addWidget(cancel_button)

        dialog_layout.addLayout(buttons_layout)

        select_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        instance_list.itemDoubleClicked.connect(
            lambda item: dialog.accept()
        )

        if dialog.exec() != QDialog.Accepted:
            return

        selected_item = instance_list.currentItem()

        if selected_item is None:
            QMessageBox.warning(
                self,
                "Выбор не сделан",
                "Выберите экземпляр из списка."
            )
            return

        instance_id = selected_item.data(Qt.UserRole)

        for row in range(self.items_table.rowCount()):
            product_item = self.items_table.item(row, 0)

            if (
                product_item is not None
                and product_item.data(Qt.UserRole + 1) == instance_id
            ):
                QMessageBox.information(
                    self,
                    "Уже добавлен",
                    "Этот экземпляр уже добавлен в закупку."
                )
                return

        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        product_item = QTableWidgetItem(selected_item.text())
        product_item.setData(Qt.UserRole + 1, instance_id)
        product_item.setData(Qt.UserRole, None)

        count_item = QTableWidgetItem("1")

        self.items_table.setItem(row, 0, product_item)
        self.items_table.setItem(row, 1, count_item)
    def remove_product(self):
        row = self.items_table.currentRow()

        if row < 0:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Выберите товар для удаления."
            )
            return

        self.items_table.removeRow(
            row
        )

    def show_context_menu(self, position):
        item = self.items_table.itemAt(position)

        if item is None:
            return

        row = item.row()

        product_item = self.items_table.item(row, 0)

        if product_item is None:
            return

        existing_instance_id = product_item.data(
            Qt.UserRole + 1
        )

        product_id = product_item.data(1000)
        listed_date = None

        # Для существующего экземпляра получаем данные из БД
        if existing_instance_id is not None:
            connection = get_connection()

            try:
                result = connection.execute(
                    """
                    SELECT product_id, listed_date
                    FROM instances
                    WHERE id = ?
                      AND deleted = 0
                    """,
                    (existing_instance_id,)
                ).fetchone()

                if result is None:
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        "Экземпляр не найден или удалён."
                    )
                    return

                product_id, listed_date = result

            finally:
                connection.close()

        if not product_id:
            return

        menu = QMenu(self)

        open_product_action = menu.addAction(
            "Открыть карточку товара"
        )

        open_instance_action = None

        if existing_instance_id is not None:
            open_instance_action = menu.addAction(
                "Открыть карточку экземпляра"
            )

        delete_row_action = None

        if not self.purchase_saved:
            menu.addSeparator()

            delete_row_action = menu.addAction(
                "Удалить строку из документа"
            )

        action = menu.exec(
            self.items_table.mapToGlobal(position)
        )

        if action == open_product_action:
            self.main_window.open_product_card(product_id)

        elif (
            open_instance_action is not None
            and action == open_instance_action
        ):
            self.main_window.open_instance_card(
                existing_instance_id
            )

        elif (
            delete_row_action is not None
            and action == delete_row_action
        ):
            self.items_table.removeRow(row)

    def load_purchase(self, purchase_id):
        from models.purchase import get_purchases, get_purchase_items

        purchase = None

        for item in get_purchases():
            if item[0] == purchase_id:
                purchase = item
                break

        if purchase is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Закупка не найдена."
            )
            return

        (
            purchase_id,
            purchase_number,
            purchase_date,
            total_purchase_price,
            total_shipping
        ) = purchase

        self.purchase_date.setDate(
            QDate.fromString(
                purchase_date,
                "yyyy-MM-dd"
            )
        )

        self.total_purchase_price.setValue(
            total_purchase_price
        )

        self.total_shipping.setValue(
            total_shipping
        )

        self.items_table.setRowCount(0)

        purchase_items = get_purchase_items(purchase_id)

        products_count = {}

        for item in purchase_items:
            (
                purchase_item_id,
                instance_id,
                internal_number,
                product_id,
                manufacturer,
                part_number,
                name,
                allocated_price,
                allocated_shipping,
                status,
                write_off_comment,
            ) = item

            if product_id not in products_count:
                products_count[product_id] = {
                    "text": " | ".join(
                        part
                        for part in [
                            manufacturer,
                            part_number,
                            name
                        ]
                        if part
                    ),
                    "count": 0
                }

            products_count[product_id]["count"] += 1

        for product_id, data in products_count.items():
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)

            product_item = QTableWidgetItem(
                data["text"]
            )
            product_item.setData(
                1000,
                product_id
            )

            count_item = QTableWidgetItem(
                str(data["count"])
            )

            self.items_table.setItem(
                row,
                0,
                product_item
            )

            self.items_table.setItem(
                row,
                1,
                count_item
            )

        # Переводим карточку в состояние после сохранения
        self.purchase_saved = True

        self.product_search.clear()
        self.product_list.clear()

        self.product_image_pixmap = QPixmap()
        self.product_image.clear()
        self.product_image.setText("Фото товара")

        self.product_search.setEnabled(False)
        self.count.setEnabled(False)
        self.add_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.purchase_date.setEnabled(False)
        self.total_purchase_price.setEnabled(False)
        self.total_shipping.setEnabled(False)

    def save_purchase(self):
        items = []
        existing_instance_ids = []

        for row in range(self.items_table.rowCount()):
            product_item = self.items_table.item(row, 0)
            count_item = self.items_table.item(row, 1)

            if product_item is None or count_item is None:
                continue

            existing_instance_id = product_item.data(
                Qt.UserRole + 1
            )

            if existing_instance_id is not None:
                existing_instance_ids.append(
                    existing_instance_id
                )
                continue

            product_id = product_item.data(1000)

            if product_id is None:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"Не удалось определить товар в строке {row + 1}."
                )
                return

            try:
                count = int(count_item.text())
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"Некорректное количество в строке {row + 1}."
                )
                return

            if count <= 0:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Количество должно быть больше нуля."
                )
                return

            items.append({
                "product_id": product_id,
                "count": count
            })

        if not items and not existing_instance_ids:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Добавьте хотя бы один товар или экземпляр."
            )
            return

        total_purchase_price = self.total_purchase_price.value()
        total_shipping = self.total_shipping.value()

        purchase_date = (
            self.purchase_date.date()
            .toString("yyyy-MM-dd")
        )

        try:
            purchase_id, purchase_number = create_purchase_multi(
                items=items,
                total_purchase_price=total_purchase_price,
                total_shipping=total_shipping,
                purchase_date=purchase_date,
                existing_instance_ids=existing_instance_ids
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка",
                str(error)
            )
            return

        QMessageBox.information(
            self,
            "Готово",
            f"Закупка №{purchase_number:05d} сохранена."
        )

        self.purchase_saved = True

        self.product_search.clear()
        self.product_list.clear()

        self.product_image_pixmap = QPixmap()
        self.product_image.clear()
        self.product_image.setText("Фото товара")

        self.product_search.setEnabled(False)
        self.product_list.setEnabled(False)
        self.count.setEnabled(False)
        self.add_button.setEnabled(False)
        self.add_existing_instance_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.purchase_date.setEnabled(False)
        self.total_purchase_price.setEnabled(False)
        self.total_shipping.setEnabled(False)

    def show_product_list_context_menu(self, position):
        item = self.product_list.itemAt(position)

        if item is None:
            return

        product_id = item.data(1000)

        if not product_id:
            return

        menu = QMenu(self)

        open_action = menu.addAction(
            "Открыть карточку товара"
        )

        action = menu.exec(
            self.product_list.mapToGlobal(position)
        )

        if action == open_action:
            self.main_window.open_product_card(
                product_id
            )