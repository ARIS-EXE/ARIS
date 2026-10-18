from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QApplication,
    QStyle,
    QDialog,
    QLabel,
    QHeaderView,
    QStyleOptionHeader,
)

from database.database import get_connection
from pathlib import Path


from app_paths import IMAGE_DIR
class ImageCanvas(QWidget):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)

        self.original_pixmap = pixmap

        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.dragging = False
        self.last_mouse_position = None

        self.setMouseTracking(True)

    def paintEvent(self, event):
        if self.original_pixmap.isNull():
            return

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform
        )

        available_width = self.width()
        available_height = self.height()

        if (
            available_width <= 0
            or available_height <= 0
        ):
            return

        # Изображение, вписанное в окно
        base_pixmap = self.original_pixmap.scaled(
            available_width,
            available_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Применяем текущий масштаб
        width = int(
            base_pixmap.width() * self.scale
        )

        height = int(
            base_pixmap.height() * self.scale
        )

        scaled_pixmap = base_pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        image_width = scaled_pixmap.width()
        image_height = scaled_pixmap.height()

        # Положение изображения без смещения
        center_x = (
            available_width - image_width
        ) // 2

        center_y = (
            available_height - image_height
        ) // 2

        # Максимальное смещение.
        # Оставляем минимум 20% изображения
        # внутри области просмотра.
        max_offset_x = int(
            image_width * 0.4
        )

        max_offset_y = int(
            image_height * 0.4
        )

        # Ограничиваем текущее смещение
        self.offset_x = max(
            -max_offset_x,
            min(
                self.offset_x,
                max_offset_x
            )
        )

        self.offset_y = max(
            -max_offset_y,
            min(
                self.offset_y,
                max_offset_y
            )
        )

        x = center_x + self.offset_x
        y = center_y + self.offset_y

        painter.drawPixmap(
            x,
            y,
            scaled_pixmap
        )

        painter.end()
    def wheelEvent(self, event):
        delta = event.angleDelta().y()

        old_scale = self.scale

        if delta > 0:
            self.scale *= 1.15
        elif delta < 0:
            self.scale /= 1.15

        # Ограничение масштаба:
        # 50% - 300%
        self.scale = max(
            0.5,
            min(self.scale, 3.0)
        )

        if self.scale != old_scale:
            self.update()

        event.accept()

    def mousePressEvent(self, event):
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.dragging = True

            self.last_mouse_position = (
                event.position().toPoint()
            )

            self.setCursor(
                Qt.CursorShape.ClosedHandCursor
            )

        event.accept()

    def mouseMoveEvent(self, event):
        if (
            self.dragging
            and self.last_mouse_position is not None
        ):
            current_position = (
                event.position().toPoint()
            )

            delta = (
                current_position
                - self.last_mouse_position
            )

            self.offset_x += delta.x()
            self.offset_y += delta.y()

            self.last_mouse_position = (
                current_position
            )

            self.update()

        event.accept()

    def mouseReleaseEvent(self, event):
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.dragging = False
            self.last_mouse_position = None

            self.setCursor(
                Qt.CursorShape.ArrowCursor
            )

        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # При изменении размера окна
        # возвращаем изображение в центр.
        self.offset_x = 0
        self.offset_y = 0

        self.update()
class ImageViewer(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Изображение товара")

        # Размер окна просмотра
        self.resize(900, 700)

        # Не позволяем окну становиться слишком маленьким
        self.setMinimumSize(500, 400)

        pixmap = QPixmap(
            str(image_path)
        )

        self.image_canvas = ImageCanvas(
            pixmap,
            self
        )

        self.close_button = QPushButton(
            "Закрыть"
        )

        self.close_button.clicked.connect(
            self.accept
        )

        layout = QVBoxLayout(self)

        layout.addWidget(
            self.image_canvas,
            1
        )

        layout.addWidget(
            self.close_button
        )
class InventoryHeader(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

        self.sort_column = None
        self.sort_order = Qt.SortOrder.AscendingOrder
        self.setSortIndicatorShown(False)

    def paintSection(self, painter, rect, logical_index):
        if not rect.isValid():
            return

        option = QStyleOptionHeader()
        self.initStyleOption(option)
        self.initStyleOptionForIndex(
            option,
            logical_index
        )

        option.rect = rect
        option.textAlignment = (
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft
        )

        is_sorted = (
            self.sort_column is not None
            and logical_index == self.sort_column
            and logical_index != 0
        )

        if is_sorted:
            option.text = "   " + option.text

        option.sortIndicator = (
            QStyleOptionHeader.SortIndicator.None_
        )

        self.style().drawControl(
            QStyle.ControlElement.CE_Header,
            option,
            painter,
            self
        )

        if is_sorted:
            arrow = (
                "↓"
                if self.sort_order
                == Qt.SortOrder.AscendingOrder
                else "↑"
            )

            painter.save()
            painter.setPen(
                self.palette().color(
                    self.foregroundRole()
                )
            )

            painter.drawText(
                rect.adjusted(6, 0, -4, 0),
                Qt.AlignmentFlag.AlignVCenter
                | Qt.AlignmentFlag.AlignLeft,
                arrow
            )
            painter.restore()
class InventoryTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        tree = self.treeWidget()

        if tree is None:
            return self.text(0).casefold() < other.text(0).casefold()

        column = tree.header().sortIndicatorSection()

        if column == 5:
            self_value = self.data(
                5,
                Qt.ItemDataRole.UserRole
            )
            other_value = other.data(
                5,
                Qt.ItemDataRole.UserRole
            )

            return int(self_value or 0) < int(other_value or 0)

        return (
            self.text(column).casefold()
            < other.text(column).casefold()
        )
class Inventory(QWidget):
    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window

        self.products_data = []
        self.expanded_product_ids = set()
        self.sort_column = None
        self.sort_order = Qt.SortOrder.AscendingOrder
        main_layout = QVBoxLayout(self)

        # Поиск
        search_layout = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Поиск по производителю, артикулу, названию или штрихкоду..."
        )

        search_button = QPushButton("Найти")
        search_button.clicked.connect(
            self.load_products
        )

        self.search.returnPressed.connect(
            self.load_products
        )

        search_layout.addWidget(self.search)
        search_layout.addWidget(search_button)

        main_layout.addLayout(search_layout)

        # Фильтры
        filters_layout = QHBoxLayout()

        self.filter_in_stock = QCheckBox("В наличии")
        self.filter_sold = QCheckBox("Проданные")
        self.filter_all = QCheckBox("Все")

        self.filter_in_stock.setChecked(True)

        self.filter_in_stock.stateChanged.connect(
            self.on_filter_changed
        )

        self.filter_sold.stateChanged.connect(
            self.on_filter_changed
        )
        self.filter_all.stateChanged.connect(
            self.on_filter_changed
        )

        filters_layout.addWidget(
            self.filter_in_stock
        )

        filters_layout.addWidget(
            self.filter_sold
        )

        filters_layout.addWidget(
            self.filter_all
        )

        filters_layout.addStretch()

        main_layout.addLayout(filters_layout)

        # Дерево склада
        self.tree = QTreeWidget()
        self.tree.setHeader(
            InventoryHeader(
                Qt.Orientation.Horizontal,
                self.tree
            )
        )
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.installEventFilter(self)
        self.tree.setHeaderLabels([
            "Фото",
            "Производитель",
            "Артикул",
            "Название",
            "Штрихкод",
            "Количество",
        ])
        header = self.tree.header()
        header.setSectionsClickable(True)
        header.setHighlightSections(False)
        header.sectionClicked.connect(
            self.sort_products_by_column
        )
        self.tree.setSortingEnabled(False)

        header = self.tree.header()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)

        self.tree.itemDoubleClicked.connect(
            self.on_tree_double_click
        )
        self.tree.itemExpanded.connect(
            self.on_item_expanded
        )
        self.tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.tree.customContextMenuRequested.connect(
            self.show_context_menu
        )

        main_layout.addWidget(self.tree)
        # Сохранение ширины столбцов склада
        self.header_settings = QSettings(
            "ARIS",
            "Inventory"
        )

        header = self.tree.header()
        saved_widths = self.header_settings.value(
            "tree_column_widths"
        )

        if saved_widths:
            for column, width in enumerate(saved_widths):
                if column < header.count():
                    header.resizeSection(
                        column,
                        int(width)
                    )

        header.sectionResized.connect(
            self.save_header_state
        )

        self.tree.header().sectionResized.connect(
            self.save_header_state
        )
    def sort_products_by_column(self, column):
        if column == self.sort_column:
            self.sort_order = (
                Qt.SortOrder.DescendingOrder
                if self.sort_order
                == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self.sort_column = column
            self.sort_order = Qt.SortOrder.AscendingOrder

        header = self.tree.header()
        header.sort_column = self.sort_column
        header.sort_order = self.sort_order

        header.setSortIndicatorShown(False)
        header.setSortIndicator(
            -1,
            self.sort_order
        )
        header.viewport().update()

        self.tree.sortItems(
            self.sort_column,
            self.sort_order
        )
    def save_header_state(self, *args):
        header = self.tree.header()

        widths = [
            header.sectionSize(column)
            for column in range(header.count())
        ]

        self.header_settings.setValue(
            "tree_column_widths",
            widths
        )
    def on_tree_double_click(self, item, column):
        if item.parent() is not None:
            return

        if column == 0:
            self.open_product_image(item)
            return

        self.toggle_tree_item(item, column)
    def on_item_expanded(self, item):
        if item.parent() is not None:
            return

        product_id = item.data(
            0,
            Qt.ItemDataRole.UserRole
        )

        if product_id is None:
            return

        if item.childCount() == 0:
            self.load_instances(
                item,
                int(product_id)
            )
    def save_expanded_state(self):
        self.expanded_product_ids.clear()

        for i in range(
            self.tree.topLevelItemCount()
        ):
            item = self.tree.topLevelItem(i)

            if item.isExpanded():
                product_id = item.data(
                    0,
                    Qt.ItemDataRole.UserRole
                )

                if product_id is not None:
                    self.expanded_product_ids.add(
                        int(product_id)
                    )

    def restore_expanded_state(self):
        for i in range(
            self.tree.topLevelItemCount()
        ):
            item = self.tree.topLevelItem(i)

            product_id = item.data(
                0,
                Qt.ItemDataRole.UserRole
            )

            if product_id is None:
                continue

            item.setExpanded(
                int(product_id)
                in self.expanded_product_ids
            )
    def hideEvent(self, event):
        self.save_expanded_state()
        super().hideEvent(event)
    def load_products(self):
        search_text = self.search.text().strip()

        category_id = getattr(
            self,
            "category_filter_id",
            None
        )

        connection = get_connection()

        try:
            conditions = ["products.deleted = 0"]
            parameters = []

            if category_id is not None:
                conditions.append(
                    """
                    products.category_id IN (
                        WITH RECURSIVE category_tree(id) AS (
                            SELECT id
                            FROM categories
                            WHERE id = ?

                            UNION ALL

                            SELECT categories.id
                            FROM categories
                            JOIN category_tree
                                ON categories.parent_id = category_tree.id
                        )
                        SELECT id
                        FROM category_tree
                    )
                    """
                )
                parameters.append(category_id)

            if search_text:
                search_words = search_text.split()

                for word in search_words:
                    pattern = f"%{word}%"

                    conditions.append(
                        """
                        (
                            products.manufacturer LIKE ?
                            OR products.part_number LIKE ?
                            OR products.name LIKE ?
                            OR products.barcode LIKE ?
                        )
                        """
                    )

                    parameters.extend([
                        pattern,
                        pattern,
                        pattern,
                        pattern,
                    ])

            if conditions:
                where_sql = (
                    "WHERE "
                    + " AND ".join(conditions)
                )
            else:
                where_sql = ""

            cursor = connection.execute(
                f"""
                SELECT
                    products.id,
                    products.manufacturer,
                    products.part_number,
                    products.name,
                    products.barcode,
                    products.deleted,
                    products.image_path,

                    SUM(
                        CASE
                            WHEN instances.deleted = 0
                                 AND instances.status = 'in_stock'
                            THEN 1
                            ELSE 0
                        END
                    ) AS in_stock_count,

                    SUM(
                        CASE
                            WHEN instances.deleted = 0
                                 AND instances.status = 'sold'
                            THEN 1
                            ELSE 0
                        END
                    ) AS sold_count,

                    SUM(
                        CASE
                            WHEN instances.deleted = 1
                            THEN 1
                            ELSE 0
                        END
                    ) AS deleted_count,

                    SUM(
                        CASE
                            WHEN instances.deleted = 0
                                 AND instances.status = 'written_off'
                            THEN 1
                            ELSE 0
                        END
                    ) AS written_off_count

                FROM products

                LEFT JOIN instances
                    ON instances.product_id = products.id

                {where_sql}

                GROUP BY
                    products.id,
                    products.manufacturer,
                    products.part_number,
                    products.name,
                    products.barcode,
                    products.deleted,
                    products.image_path

                ORDER BY
                    products.name COLLATE NOCASE
                """,
                parameters,
            )

            self.products_data = cursor.fetchall()

        finally:
            connection.close()

        self.apply_filters()

    def apply_filters(self):
        self.save_expanded_state()

        show_in_stock = self.filter_in_stock.isChecked()
        show_sold = self.filter_sold.isChecked()
        show_all = self.filter_all.isChecked()

        self.tree.clear()

        for product in self.products_data:
            product_id = product[0]

            in_stock_count = product[7] or 0
            sold_count = product[8] or 0
            deleted_count = product[9] or 0
            written_off_count = product[10] or 0
            image_filename = product[6]

            # Определяем, должен ли товар отображаться
            if show_all:
                visible = True

            else:
                visible = (
                    (show_in_stock and in_stock_count > 0)
                    or
                    (show_sold and sold_count > 0)
                )

            if not visible:
                continue

            # Определяем количество
            if show_all:
                quantity = (
                    in_stock_count
                    + sold_count
                    + written_off_count
                )

            else:
                quantity = 0

                if show_in_stock:
                    quantity += in_stock_count

                if show_sold:
                    quantity += sold_count

            product_item = InventoryTreeWidgetItem([
                "",
                product[1] or "",
                product[2] or "",
                product[3] or "",
                product[4] or "",
                str(quantity),
            ])
            product_item.setData(
                5,
                Qt.ItemDataRole.UserRole,
                int(quantity or 0)
            )
            product_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                product_id
            )

            product_item.setData(
                0,
                Qt.ItemDataRole.UserRole + 3,
                image_filename
            )

            # Иконка изображения
            if image_filename:
                icon = QApplication.style().standardIcon(
                    QStyle.StandardPixmap.SP_FileIcon
                )
            else:
                icon = QApplication.style().standardIcon(
                    QStyle.StandardPixmap.SP_MessageBoxWarning
                )

            product_item.setIcon(
                0,
                icon
            )

            if (
                in_stock_count > 0
                or sold_count > 0
                or deleted_count > 0
            ):
                product_item.setChildIndicatorPolicy(
                    QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                )

            self.tree.addTopLevelItem(
                product_item
            )

        self.restore_expanded_state()
    def on_filter_changed(self):
        sender = self.sender()

        if sender is self.filter_all:
            if self.filter_all.isChecked():
                self.filter_in_stock.blockSignals(True)
                self.filter_sold.blockSignals(True)

                self.filter_in_stock.setChecked(False)
                self.filter_sold.setChecked(False)

                self.filter_in_stock.blockSignals(False)
                self.filter_sold.blockSignals(False)

        else:
            if sender.isChecked():
                self.filter_all.blockSignals(True)
                self.filter_all.setChecked(False)
                self.filter_all.blockSignals(False)

        self.apply_filters()

    def load_instances(self, product_item, product_id):
        from models.instance import get_instances_by_product

        instances = get_instances_by_product(
            product_id
        )
        show_in_stock = self.filter_in_stock.isChecked()
        show_sold = self.filter_sold.isChecked()
        show_all = self.filter_all.isChecked()
        condition_names = {
            "new": "Новый",
            "used": "Б/у",
            "defective": "Неисправен",
            "parts": "На запчасти",
        }

        status_names = {
            "in_stock": "В наличии",
            "sold": "Продан",
            "written_off": "Списан",
        }

        for instance in instances:
            instance_status = instance[7]

            if show_all:
                pass

            elif (
                instance_status == "in_stock"
                and show_in_stock
            ):
                pass

            elif (
                instance_status == "sold"
                and show_sold
            ):
                pass

            else:
                continue
            condition = condition_names.get(
                instance[3],
                instance[3]
            )

            status = status_names.get(
                instance[7],
                instance[7]
            )

            product_text = (
                f"Экземпляр №{instance[1]}"
            )

            instance_item = QTreeWidgetItem([
                "",
                product_text,
                "",
                condition,
                "",
                (
                    f"Закупка: {instance[4] or 0}  | "
                    f"Доставка: {instance[5] or 0}  | "
                    f"{instance[6]} | "
                    f"{status}"
                ),
            ])

            instance_item.setData(
                0,
                Qt.ItemDataRole.UserRole + 1,
                instance[0]
            )
            instance_item.setData(
                0,
                Qt.ItemDataRole.UserRole + 2,
                product_id
            )
            if status == "Продан":
                light_green = QColor("#DDF0DD")

                for column in range(6):
                    instance_item.setBackground(
                        column,
                        light_green
                    )

            elif status == "Списан":
                for column in range(6):
                    instance_item.setBackground(
                        column,
                        QColor("#E6A0A0")
                    )

            elif instance[11]:
                light_yellow = QColor("#FFF2CC")

                for column in range(6):
                    instance_item.setBackground(
                        column,
                        light_yellow
                    )

            product_item.addChild(
                instance_item
            )

    def toggle_tree_item(self, item, column):
        if item.parent() is not None:
            return

        if item.isExpanded():
            item.setExpanded(False)
            return

        item.setExpanded(True)
    def open_product_image(self, item):
        if item.parent() is not None:
            return

        image_filename = item.data(
            0,
            Qt.ItemDataRole.UserRole + 3
        )

        if not image_filename:
            return

        image_path = IMAGE_DIR / image_filename

        if not image_path.exists():
            return

        viewer = ImageViewer(
            image_path,
            self
        )

        viewer.exec()

    def eventFilter(self, obj, event):
        if (
            obj is self.tree
            and event.type() == event.Type.KeyPress
            and event.key() == Qt.Key_C
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            item = self.tree.currentItem()

            if item is None:
                return True

            values = [
                item.text(column)
                for column in range(self.tree.columnCount())
            ]

            QApplication.clipboard().setText(
                "\t".join(values)
            )

            return True

        return super().eventFilter(obj, event)

    def show_context_menu(self, position):
        item = self.tree.itemAt(position)

        if item is None:
            return

        instance_id = item.data(
            0,
            Qt.ItemDataRole.UserRole + 1
        )

        instance_product_id = item.data(
            0,
            Qt.ItemDataRole.UserRole + 2
        )

        product_id = item.data(
            0,
            Qt.ItemDataRole.UserRole
        )

        menu = QMenu(self)

        if instance_id is not None:
            product_action = menu.addAction(
                "Открыть карточку товара"
            )
            product_action.triggered.connect(
                lambda: self.main_window.open_product_card(
                    int(instance_product_id)
                )
            )
            action = menu.addAction(
                "Открыть карточку экземпляра"
            )

            action.triggered.connect(
                lambda: self.main_window.open_instance_card(
                    int(instance_id)
                )
            )

        elif product_id is not None:
            action = menu.addAction(
                "Открыть карточку товара"
            )

            action.triggered.connect(
                lambda: self.main_window.open_product_card(
                    int(product_id)
                )
            )

        else:
            return

        menu.exec(
            self.tree.viewport().mapToGlobal(position)
        )