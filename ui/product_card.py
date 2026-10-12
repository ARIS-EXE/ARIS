from datetime import datetime
from pathlib import Path
import shutil
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QComboBox,
    QTextEdit,
    QFileDialog,
    QGroupBox,
    QMenu,
)

from database.database import get_connection
from ui.category_selector import CategorySelector


from app_paths import IMAGE_DIR

MAX_IMAGE_SIZE = 2 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


class ProductCard(QWidget):
    def __init__(
        self,
        product_id=None,
        allow_deleted=False
    ):
        super().__init__()

        self.product_id = product_id
        self.allow_deleted = allow_deleted
        # Путь к уже сохранённому изображению.
        self.image_filename = None

        # Временный файл, выбранный до первого сохранения товара.
        self.pending_image_path = None

        self.setWindowTitle(
            "Новый товар"
            if product_id is None
            else "Карточка товара"
        )

        self.resize(750, 750)

        main_layout = QVBoxLayout(self)

        # =========================================================
        # Заголовок
        # =========================================================

        title = QLabel(
            "Новый товар"
            if product_id is None
            else "Карточка товара"
        )

        title.setStyleSheet(
            "font-size: 22px; font-weight: bold;"
        )

        main_layout.addWidget(title)

        # =========================================================
        # Верхняя часть: данные + изображение
        # =========================================================

        top_layout = QHBoxLayout()

        # ---------------------------------------------------------
        # Левая часть — основные данные + настройки продажи
        # ---------------------------------------------------------

        left_layout = QVBoxLayout()

        form = QFormLayout()

        self.product_id_label = QLabel(
            "—"
            if self.product_id is None
            else str(self.product_id)
        )

        self.product_id_label.setStyleSheet(
            "color: #666666; font-weight: bold;"
        )

        self.barcode = QLineEdit()
        self.barcode.setPlaceholderText("Необязательно")
        self.barcode.setMaximumWidth(220)

        self.manufacturer = QLineEdit()
        self.manufacturer.setMaximumWidth(280)

        self.part_number = QLineEdit()
        self.part_number.setMaximumWidth(280)

        self.name = QLineEdit()

        self.category_id = None

        self.category = QPushButton(
            "Выбрать категорию"
        )

        self.category.clicked.connect(
            self.select_category
        )

        self.manufacturer_price = QSpinBox()
        self.manufacturer_price.setRange(
            0,
            10_000_000
        )
        self.manufacturer_price.setSuffix(" ¥")
        self.manufacturer_price.setFixedWidth(150)

        form.addRow("ID товара:", self.product_id_label)
        form.addRow("Штрихкод:", self.barcode)
        form.addRow("Производитель:", self.manufacturer)
        form.addRow("Артикул:", self.part_number)
        form.addRow("Название:", self.name)
        form.addRow("Категория:", self.category)

        # ---------------------------------------------------------
        # Продажные настройки
        # ---------------------------------------------------------

        self.packaging = QSpinBox()
        self.packaging.setRange(
            0,
            10_000_000
        )
        self.packaging.setSuffix(" ¥")
        self.packaging.setFixedWidth(150)

        self.buyer_shipping = QSpinBox()
        self.buyer_shipping.setRange(
            0,
            10_000_000
        )
        self.buyer_shipping.setSuffix(" ¥")

        self.delivery_option = QComboBox()
        self.delivery_option.addItem("Не выбран", None)
        self.load_delivery_options()

        self.delivery_option.activated.connect(
            self.on_delivery_option_changed
        )

        self.commission_type = QComboBox()

        self.commission_type.addItem(
            "%",
            "percent"
        )

        self.commission_type.addItem(
            "¥",
            "fixed"
        )

        self.commission_type.currentIndexChanged.connect(
            self.update_commission_suffix
        )
        self.commission_value = QDoubleSpinBox()
        self.commission_value.setDecimals(2)
        self.commission_value.setRange(0, 100)
        self.commission_value.setSuffix(" %")

        commission_layout = QHBoxLayout()
        commission_layout.setContentsMargins(0, 0, 0, 0)
        commission_layout.setSpacing(5)

        commission_layout.addWidget(
            self.commission_type
        )

        commission_layout.addWidget(
            self.commission_value
        )

        # ---------------------------------------------------------
        # Цена + упаковка слева
        # ---------------------------------------------------------

        left_sale_form = QFormLayout()
        left_sale_form.setContentsMargins(0, 10, 0, 0)

        left_sale_form.addRow(
            "Цена производителя:",
            self.manufacturer_price
        )

        left_sale_form.addRow(
            "Упаковка:",
            self.packaging
        )

        # ---------------------------------------------------------
        # Доставка + комиссия справа
        # ---------------------------------------------------------

        right_sale_form = QFormLayout()
        right_sale_form.setContentsMargins(0, 10, 0, 0)

        right_sale_form.addRow(
            "Доставка покупателя:",
            self.buyer_shipping
        )
        left_sale_form.addRow("Вариант доставки:", self.delivery_option)
        right_sale_form.addRow(
            "Комиссия Yahoo:",
            commission_layout
        )

        # ---------------------------------------------------------
        # Общая область продажных настроек
        # ---------------------------------------------------------

        sale_columns = QHBoxLayout()
        sale_columns.setContentsMargins(0, 0, 0, 0)
        sale_columns.setSpacing(60)

        sale_columns.addLayout(
            left_sale_form
        )

        sale_columns.addSpacing(20)

        sale_columns.addLayout(
            right_sale_form
        )

        sale_columns.addStretch()

        left_layout.addLayout(form)

        left_layout.addLayout(
            sale_columns
        )

        # ---------------------------------------------------------
        # Правая часть — изображение
        # ---------------------------------------------------------

        image_group = QGroupBox(
            "Изображение"
        )

        image_layout = QVBoxLayout()

        self.image_label = QLabel()

        self.image_label.setFixedSize(
            200,
            200
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setStyleSheet(
            """
            QLabel {
                border: 1px solid #bdbdbd;
                background: #f5f5f5;
            }
            """
        )

        image_layout.addWidget(
            self.image_label,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        image_buttons = QHBoxLayout()

        self.load_image_button = QPushButton(
            "Загрузить"
        )

        self.delete_image_button = QPushButton(
            "Удалить"
        )

        image_buttons.addWidget(
            self.load_image_button
        )

        image_buttons.addWidget(
            self.delete_image_button
        )

        image_layout.addLayout(
            image_buttons
        )

        self.show_image_folder_button = QPushButton(
            "Показать в папке"
        )

        image_layout.addWidget(
            self.show_image_folder_button
        )

        image_group.setLayout(
            image_layout
        )

        # ---------------------------------------------------------
        # Собираем верхнюю часть
        # ---------------------------------------------------------

        top_layout.addLayout(
            left_layout,
            1
        )

        top_layout.addWidget(
            image_group
        )

        main_layout.addLayout(
            top_layout
        )

        # Описание
        main_layout.addWidget(QLabel("Описание:"))

        self.description = QTextEdit()
        self.description.setMaximumHeight(110)
        main_layout.addWidget(self.description)

        # Заметки
        main_layout.addWidget(QLabel("Заметки:"))

        self.notes = QTextEdit()
        self.notes.setMaximumHeight(90)
        main_layout.addWidget(self.notes)

        # =========================================================
        # Экземпляры
        # =========================================================

        self.instances_label = QLabel(
            "Экземпляры (0)"
        )

        self.instances_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        main_layout.addWidget(
            self.instances_label
        )

        self.instances_list = QListWidget()

        self.instances_list.itemDoubleClicked.connect(
            self.open_instance
        )
        self.instances_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.instances_list.customContextMenuRequested.connect(
            self.show_instance_context_menu
        )
        main_layout.addWidget(
            self.instances_list
        )

        # =========================================================
        # Кнопки
        # =========================================================

        buttons_layout = QHBoxLayout()

        self.add_instance_button = QPushButton(
            "+ Добавить экземпляр"
        )
        self.delete_product_button = QPushButton(
            "Удалить товар"
        )

        self.delete_product_button.setEnabled(False)

        self.delete_product_button.setToolTip(
            "Удаление невозможно: у товара есть экземпляры в наличии."
        )
        self.save_button = QPushButton(
            "Сохранить"
        )

        self.save_close_button = QPushButton(
            "Сохранить и закрыть"
        )

        buttons_layout.addWidget(
            self.add_instance_button
        )

        buttons_layout.addWidget(
            self.delete_product_button
        )
        buttons_layout.addWidget(
            self.save_button
        )

        buttons_layout.addWidget(
            self.save_close_button
        )

        main_layout.addLayout(
            buttons_layout
        )

        # =========================================================
        # Сигналы
        # =========================================================

        self.load_image_button.clicked.connect(
            self.load_image
        )

        self.delete_image_button.clicked.connect(
            self.delete_image
        )

        self.show_image_folder_button.clicked.connect(
            self.show_image_in_folder
        )

        self.add_instance_button.clicked.connect(
            self.add_instance
        )
        self.delete_product_button.clicked.connect(
            self.delete_product
        )
        self.save_button.clicked.connect(
            self.save
        )

        self.save_close_button.clicked.connect(
            self.save_and_close
        )

        # =========================================================
        # Начальное состояние
        # =========================================================

        self.update_commission_suffix()

        if self.product_id is not None:
            self.load_product()
            self.load_instances()

            if self.allow_deleted:
                self.add_instance_button.setEnabled(False)
                self.delete_product_button.setEnabled(False)
        else:
            self.update_image_buttons()
            self.update_delete_button()

    # =============================================================
    # Категория
    # =============================================================

    def get_category_path(self, category_id):
        if category_id is None:
            return ""

        connection = get_connection()

        try:
            path = []
            current_id = category_id

            while current_id is not None:
                cursor = connection.execute(
                    """
                    SELECT name, parent_id
                    FROM categories
                    WHERE id = ?
                    """,
                    (current_id,)
                )

                category = cursor.fetchone()

                if category is None:
                    break

                name, parent_id = category

                path.insert(0, name)
                current_id = parent_id

            return " → ".join(path)

        finally:
            connection.close()

    def select_category(self):
        dialog = CategorySelector(self)

        if dialog.exec():
            self.category_id = (
                dialog.selected_category_id
            )

            category_path = self.get_category_path(
                self.category_id
            )

            self.category.setText(
                category_path
            )

    # =============================================================
    # Изображение
    # =============================================================

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение",
            "",
            "Изображения (*.jpg *.jpeg *.png *.webp)"
        )

        if not file_path:
            return

        source = Path(file_path)

        if source.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
            QMessageBox.warning(
                self,
                "Неверный формат",
                "Поддерживаются только JPG, JPEG, PNG и WEBP."
            )
            return

        try:
            file_size = source.stat().st_size
        except OSError:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось прочитать выбранный файл."
            )
            return

        if file_size > MAX_IMAGE_SIZE:
            QMessageBox.warning(
                self,
                "Файл слишком большой",
                "Размер изображения не должен превышать 2 МБ."
            )
            return

        # Проверяем, что файл действительно является
        # изображением.
        pixmap = QPixmap(str(source))

        if pixmap.isNull():
            QMessageBox.warning(
                self,
                "Ошибка изображения",
                "Выбранный файл не удалось открыть как изображение."
            )
            return

        if self.product_id is None:
            # Товар ещё не сохранён.
            # Пока запоминаем исходный файл.
            self.pending_image_path = source

            self.set_image_preview(
                pixmap
            )

            self.update_image_buttons(
                has_image=True
            )

            return

        # Для существующего товара сохраняем сразу.
        if self.save_image_file(source):
            self.set_image_preview(
                pixmap
            )

    def save_image_file(self, source):
        IMAGE_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        extension = source.suffix.lower()

        new_filename = (
            f"{self.product_id}{extension}"
        )

        destination = IMAGE_DIR / new_filename

        connection = None

        try:
            # Копируем сначала во временный файл.
            temp_destination = IMAGE_DIR / (
                f".{self.product_id}_temp{extension}"
            )

            shutil.copy2(
                source,
                temp_destination
            )

            # Удаляем старое изображение, если оно есть.
            self.remove_existing_image_files(
                except_filename=new_filename
            )

            temp_destination.replace(
                destination
            )

            connection = get_connection()

            connection.execute(
                """
                UPDATE products
                SET image_path = ?
                WHERE id = ?
                """,
                (
                    new_filename,
                    self.product_id,
                )
            )

            connection.commit()

            self.image_filename = new_filename

            self.pending_image_path = None

            self.update_image_buttons()

            return True

        except Exception as error:
            if connection:
                connection.rollback()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить изображение:\n\n{error}"
            )

            return False

        finally:
            if connection:
                connection.close()

    def remove_existing_image_files(
        self,
        except_filename=None
    ):
        if self.product_id is None:
            return

        if not IMAGE_DIR.exists():
            return

        for path in IMAGE_DIR.iterdir():
            if not path.is_file():
                continue

            if path.stem != str(self.product_id):
                continue

            if (
                except_filename is not None
                and path.name == except_filename
            ):
                continue

            try:
                path.unlink()
            except OSError:
                pass

    def delete_image(self):
        if self.product_id is None:
            self.pending_image_path = None

            self.image_label.clear()

            self.update_image_buttons(
                has_image=False
            )

            return

        if not self.image_filename:
            return

        answer = QMessageBox.question(
            self,
            "Удалить изображение",
            "Удалить изображение товара?"
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        connection = None

        try:
            self.remove_existing_image_files()

            connection = get_connection()

            connection.execute(
                """
                UPDATE products
                SET image_path = NULL
                WHERE id = ?
                """,
                (self.product_id,)
            )

            connection.commit()

            self.image_filename = None

            self.image_label.clear()

            self.update_image_buttons(
                has_image=False
            )

        except Exception as error:
            if connection:
                connection.rollback()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось удалить изображение:\n\n{error}"
            )

        finally:
            if connection:
                connection.close()

    def set_image_preview(self, pixmap):
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.image_label.setPixmap(
            scaled
        )

    def load_image_preview(self):
        if self.product_id is None:
            return

        if not self.image_filename:
            self.image_label.clear()
            return

        image_path = IMAGE_DIR / self.image_filename

        if not image_path.exists():
            self.image_label.clear()
            return

        pixmap = QPixmap(
            str(image_path)
        )

        if pixmap.isNull():
            self.image_label.clear()
            return

        self.set_image_preview(
            pixmap
        )

    def update_image_buttons(self, has_image=None):
        if has_image is None:
            has_image = (
                self.image_filename is not None
                or self.pending_image_path is not None
            )

        self.delete_image_button.setEnabled(
            has_image
        )

        self.show_image_folder_button.setEnabled(
            self.image_filename is not None
            and self.product_id is not None
        )

    def show_image_in_folder(self):
        if (
            self.product_id is None
            or not self.image_filename
        ):
            return

        image_path = (
            IMAGE_DIR / self.image_filename
        )

        if not image_path.exists():
            QMessageBox.warning(
                self,
                "Файл не найден",
                "Файл изображения отсутствует."
            )
            return

        try:
            subprocess.run(
                [
                    "explorer",
                    "/select,",
                    str(image_path)
                ],
                check=False
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось открыть папку:\n\n{error}"
            )

    # =============================================================
    # Комиссия Yahoo
    # =============================================================

    def update_commission_suffix(self):
        commission_type = self.commission_type.currentData()

        if commission_type == "fixed":
            self.commission_value.setDecimals(0)
            self.commission_value.setMinimum(0)
            self.commission_value.setMaximum(100_000_000)
            self.commission_value.setSuffix(" ¥")

        else:
            self.commission_value.setDecimals(2)
            self.commission_value.setMinimum(0)
            self.commission_value.setMaximum(100)
            self.commission_value.setSuffix(" %")

    # =============================================================
    # Экземпляры
    # =============================================================
    def update_delete_button(self):
        if self.product_id is None:
            self.delete_product_button.setEnabled(False)
            self.delete_product_button.setToolTip(
                "Сначала сохраните товар."
            )
            return

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT COUNT(*)
                FROM instances
                WHERE product_id = ?
                  AND deleted = 0
                  AND status = 'in_stock'
                """,
                (self.product_id,)
            )

            in_stock_count = cursor.fetchone()[0]

        finally:
            connection.close()

        if in_stock_count > 0:
            self.delete_product_button.setEnabled(False)
            self.delete_product_button.setToolTip(
                "Удаление невозможно: "
                f"у товара есть экземпляры в наличии ({in_stock_count})."
            )

        else:
            self.delete_product_button.setEnabled(True)
            self.delete_product_button.setToolTip(
                "Переместить карточку товара в Корзину."
            )
    def delete_product(self):
        if self.product_id is None:
            return

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT COUNT(*)
                FROM instances
                WHERE product_id = ?
                  AND deleted = 0
                  AND status = 'in_stock'
                """,
                (self.product_id,)
            )

            in_stock_count = cursor.fetchone()[0]

        finally:
            connection.close()

        # Повторная проверка непосредственно перед удалением.
        if in_stock_count > 0:
            QMessageBox.warning(
                self,
                "Удаление невозможно",
                "Карточку товара нельзя удалить, "
                "пока у него есть экземпляры в наличии."
            )

            self.update_delete_button()
            return

        answer = QMessageBox.question(
            self,
            "Удалить товар",
            "Карточка товара будет перемещена в Корзину "
            "и перестанет отображаться на складе.\n\n"
            "Продолжить?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        connection = None

        try:
            connection = get_connection()

            connection.execute(
                """
                UPDATE products
                SET deleted = 1
                WHERE id = ?
                """,
                (self.product_id,)
            )

            connection.commit()

        except Exception as error:
            if connection:
                connection.rollback()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось удалить товар:\n\n{error}"
            )

            return

        finally:
            if connection:
                connection.close()

        # Закрываем текущую вкладку.
        # История вкладок MainWindow сама вернёт
        # предыдущую активную вкладку.
        window = self.window()

        if hasattr(window, "tabs"):
            index = window.tabs.indexOf(self)

            if index >= 0:
                window.tabs.removeTab(index)
                return

        self.close()
    def add_instance(self):
        if self.product_id is None:
            QMessageBox.warning(
                self,
                "Сначала сохраните товар",
                "Сначала сохраните карточку товара."
            )
            return
        answer = QMessageBox.question(
            self,
            "Добавление экземпляра напрямую",
            "Этот способ предназначен для исключительных случаев, "
            "когда экземпляр уже существует физически, "
            "но его закупка не была занесена в систему.\n\n"
            "Основной способ добавления товара на склад — "
            "через оформление закупки. Это позволяет корректно "
            "сохранить данные о закупочной цене, доставке "
            "и самой закупке.\n\n"
            "Продолжить добавление экземпляра напрямую?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return
        from models.instance import create_instance

        try:
            instance_id = create_instance(
                product_id=self.product_id
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось создать экземпляр:\n\n{error}"
            )
            return

        self.load_instances()

        QMessageBox.information(
            self,
            "Экземпляр создан",
            f"Экземпляр успешно создан.\n\n"
            f"ID экземпляра: {instance_id}"
        )

    def load_instances(self):
        if self.product_id is None:
            return

        from models.instance import get_instances_by_product

        instances = get_instances_by_product(
            self.product_id
        )

        self.instances_list.clear()

        self.instances_label.setText(
            f"Экземпляры ({len(instances)})"
        )

        condition_names = {
            "new": "Новый",
            "used": "Б/у",
            "defective": "Неисправен",
            "parts": "На запчасти"
        }

        status_names = {
            "in_stock": "В наличии",
            "sold": "Продан",
            "written_off": "Списан"
        }

        for instance in instances:
            internal_number = instance[1]

            condition = condition_names.get(
                instance[3],
                instance[3]
            )

            purchase_price = instance[4] or 0
            purchase_shipping = instance[5] or 0

            purchase_cost = (
                purchase_price
                + purchase_shipping
            )

            purchase_date = instance[6]

            status = status_names.get(
                instance[7],
                instance[7]
            )
            text = (
                f"№{internal_number}  |  "
                f"{condition}  |  "
                f"Себестоимость: {purchase_cost} ¥  |  "
                f"Закупка: {purchase_date}  |  "
                f"{status}"
            )

            item = QListWidgetItem(text)

            item.setData(
                Qt.ItemDataRole.UserRole,
                instance[0]
            )
            item.setData(
                Qt.ItemDataRole.UserRole + 1,
                instance[7]
            )
            if instance[7] == "written_off" and instance[12]:
                item.setToolTip(
                    f"Причина списания: {instance[12]}"
                )
            self.instances_list.addItem(
                item
            )
        self.update_delete_button()



    def show_instance_context_menu(self, position):
        item = self.instances_list.itemAt(position)

        if item is None:
            return

        status = item.data(
            Qt.ItemDataRole.UserRole + 1
        )

        instance_id = item.data(
            Qt.ItemDataRole.UserRole
        )

        from models.purchase import get_purchase_id_by_instance

        purchase_id = get_purchase_id_by_instance(instance_id)

        menu = QMenu(self)

        purchase_action = None
        buy_action = None
        sale_action = None

        if status in ("in_stock", "sold", "written_off"):
            if purchase_id is not None:
                purchase_action = menu.addAction(
                    "Открыть документ закупки"
                )
            else:
                buy_action = menu.addAction(
                    "Закупить"
                )

        if status == "sold":
            sale_action = menu.addAction(
                "Открыть документ продажи"
            )

        open_action = menu.addAction(
            "Открыть карточку экземпляра"
        )

        action = menu.exec(
            self.instances_list.mapToGlobal(position)
        )

        if action == open_action:
            self.open_instance(item)

        elif action == buy_action and buy_action is not None:
            self.window().open_purchase_for_instance(
                int(instance_id)
            )

        elif action == purchase_action and purchase_action is not None:
            self.window().open_purchase(
                int(purchase_id)
            )

        elif action == sale_action and sale_action is not None:
            from models.sale import get_sale_id_by_instance

            sale_id = get_sale_id_by_instance(instance_id)

            if sale_id is not None:
                self.window().open_sale(
                    int(sale_id)
                )

    def open_instance(self, item):
        instance_number = (
            item.text()
            .split("|")[0]
            .strip()
        )

        instance_number = (
            instance_number.replace("№", "")
        )

        instance_number = int(
            instance_number
        )

        from models.instance import (
            get_instance_by_number
        )

        instance = get_instance_by_number(
            instance_number
        )

        if instance is None:
            return

        instance_id = instance[0]

        window = self.window()

        if not hasattr(
            window,
            "open_instance_card"
        ):
            return

        window.open_instance_card(
            instance_id
        )

    # =============================================================
    # Загрузка товара
    # =============================================================

    def load_product(self):
        if self.allow_deleted:
            deleted_condition = ""
        else:
            deleted_condition = """
                AND deleted = 0
            """

        connection = get_connection()

        try:

            cursor = connection.execute(
                f"""
                SELECT
                    barcode,
                    manufacturer,
                    part_number,
                    name,
                    category_id,
                    description,
                    manufacturer_price,
                    notes,
                    default_packaging,
                    default_buyer_shipping,
                    default_delivery_option_id,
                    default_commission_type,
                    default_commission_value,
                    image_path
                FROM products
                WHERE id = ?
                  {deleted_condition}
                """,
                (self.product_id,)
            )

            product = cursor.fetchone()

        finally:
            connection.close()

        if product is None:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Товар не найден."
            )
            self.close()
            return

        self.product_id_label.setText(
            str(self.product_id)
        )

        self.barcode.setText(
            product[0] or ""
        )

        self.manufacturer.setText(
            product[1] or ""
        )

        self.part_number.setText(
            product[2] or ""
        )

        self.name.setText(
            product[3] or ""
        )

        self.category_id = product[4]

        category_path = self.get_category_path(
            self.category_id
        )

        self.category.setText(
            category_path
        )

        self.description.setPlainText(
            product[5] or ""
        )

        if product[6] is not None:
            self.manufacturer_price.setValue(
                product[6]
            )

        self.notes.setPlainText(
            product[7] or ""
        )

        self.packaging.setValue(
            product[8] or 0
        )

        self.buyer_shipping.setValue(
            product[9] or 0
        )

        delivery_option_id = product[10]

        delivery_index = self.delivery_option.findData(
            delivery_option_id
        )

        if delivery_index >= 0:
            self.delivery_option.setCurrentIndex(
                delivery_index
            )
        else:
            self.delivery_option.setCurrentIndex(0)

        commission_type = (
            product[11] or "percent"
        )

        index = self.commission_type.findData(
            commission_type
        )

        if index >= 0:
            self.commission_type.setCurrentIndex(
                index
            )

        self.commission_value.setValue(
            product[12] or 0
        )

        self.image_filename = (
            product[13]
            if product[13]
            else None
        )

        self.load_image_preview()

        self.update_image_buttons()


    def load_delivery_options(self):
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, name
            FROM delivery_options
            ORDER BY name COLLATE NOCASE
            """
        )

        options = cursor.fetchall()
        connection.close()

        for option_id, name in options:
            self.delivery_option.addItem(name, option_id)

    def on_delivery_option_changed(self, index):
        if self.delivery_option.currentData() is not None:
            self.packaging.setValue(0)
            self.buyer_shipping.setValue(0)


    # =============================================================
    # Сохранение
    # =============================================================

    def save(self):
        name = self.name.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Введите название товара."
            )
            return False

        connection = None

        try:
            connection = get_connection()

            commission_type = (
                self.commission_type.currentData()
            )
            delivery_option_id = (
                self.delivery_option.currentData()
            )
            if self.product_id is None:

                cursor = connection.execute(
                    """
                    INSERT INTO products (
                        barcode,
                        manufacturer,
                        part_number,
                        name,
                        category_id,
                        description,
                        manufacturer_price,
                        notes,
                        default_packaging,
                        default_buyer_shipping,
                        default_delivery_option_id,
                        default_commission_type,
                        default_commission_value,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.barcode.text().strip()
                        or None,

                        self.manufacturer.text().strip()
                        or None,

                        self.part_number.text().strip()
                        or None,

                        name,

                        self.category_id,

                        self.description.toPlainText().strip()
                        or None,

                        self.manufacturer_price.value(),

                        self.notes.toPlainText().strip()
                        or None,

                        self.packaging.value(),

                        self.buyer_shipping.value(),
                        delivery_option_id,
                        commission_type,

                        self.commission_value.value(),

                        datetime.now().isoformat(
                            timespec="seconds"
                        ),
                    )
                )

                self.product_id = cursor.lastrowid

                self.product_id_label.setText(
                    str(self.product_id)
                )

                # Если изображение было выбрано
                # до сохранения товара — теперь
                # можно сохранить его под ID товара.
                if self.pending_image_path:
                    pending_path = (
                        self.pending_image_path
                    )

                    if not self.save_image_file(
                        pending_path
                    ):
                        QMessageBox.warning(
                            self,
                            "Предупреждение",
                            "Товар сохранён, но изображение "
                            "не удалось сохранить."
                        )

            else:

                connection.execute(
                    """
                    UPDATE products
                    SET
                        barcode = ?,
                        manufacturer = ?,
                        part_number = ?,
                        name = ?,
                        category_id = ?,
                        description = ?,
                        manufacturer_price = ?,
                        notes = ?,
                        default_packaging = ?,
                        default_buyer_shipping = ?,
                        default_delivery_option_id = ?,
                        default_commission_type = ?,
                        default_commission_value = ?
                    WHERE id = ?
                    """,
                    (
                        self.barcode.text().strip()
                        or None,

                        self.manufacturer.text().strip()
                        or None,

                        self.part_number.text().strip()
                        or None,

                        name,

                        self.category_id,

                        self.description.toPlainText().strip()
                        or None,

                        self.manufacturer_price.value(),

                        self.notes.toPlainText().strip()
                        or None,

                        self.packaging.value(),

                        self.buyer_shipping.value(),
                        delivery_option_id,
                        commission_type,

                        self.commission_value.value(),

                        self.product_id,
                    )
                )

                if self.pending_image_path:
                    pending_path = (
                        self.pending_image_path
                    )

                    if not self.save_image_file(
                        pending_path
                    ):
                        QMessageBox.warning(
                            self,
                            "Предупреждение",
                            "Товар сохранён, но изображение "
                            "не удалось сохранить."
                        )

            connection.commit()

            QMessageBox.information(
                self,
                "Сохранено",
                "Товар успешно сохранён."
            )

            return True

        except Exception as error:
            if connection:
                connection.rollback()

            if "idx_products_barcode_unique" in str(
                error
            ):
                QMessageBox.warning(
                    self,
                    "Дубликат штрихкода",
                    "Товар с таким штрихкодом уже существует."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Ошибка сохранения",
                    f"Не удалось сохранить товар:\n\n{error}"
                )

            return False

        finally:
            if connection:
                connection.close()

    # =============================================================
    # Закрытие
    # =============================================================

    def save_and_close(self):
        if self.save():
            window = self.window()

            if hasattr(window, "tabs"):
                index = window.tabs.indexOf(self)

                if index >= 0:
                    window.tabs.removeTab(index)
                    return

            self.close()