from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QSplitter,
    QLineEdit,
)
from database.database import get_connection


class Trash(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.layout = QVBoxLayout(self)

        self.product_list = QTreeWidget()
        self.product_list.setColumnCount(4)
        self.product_list.setHeaderLabels([
            "ID",
            "Производитель",
            "Артикул",
            "Название",
        ])

        self.product_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.product_list.customContextMenuRequested.connect(
            self.show_context_menu
        )

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_title = QLabel("Удалённые товары")
        left_title.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        left_layout.addWidget(left_title)

        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText(
            "Поиск..."
        )

        left_layout.addWidget(
            self.product_search
        )

        left_layout.addWidget(
            self.product_list
        )

        self.written_off_list = QTreeWidget()
        self.written_off_list.setColumnCount(6)
        self.written_off_list.setHeaderLabels([
            "Дата",
            "№ экземпляра",
            "Производитель",
            "Артикул",
            "Название",
            "Причина списания",
        ])
        self.written_off_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.written_off_list.customContextMenuRequested.connect(
            self.show_written_off_context_menu
        )
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        right_title = QLabel("Списанные экземпляры")
        right_title.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        right_layout.addWidget(right_title)

        self.written_off_search = QLineEdit()
        self.written_off_search.setPlaceholderText(
            "Поиск..."
        )

        right_layout.addWidget(
            self.written_off_search
        )

        right_layout.addWidget(
            self.written_off_list
        )
        self.product_search.textChanged.connect(
            self.filter_products
        )

        self.written_off_search.textChanged.connect(
            self.filter_written_offs
        )

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        splitter.setSizes([
            400,
            600,
        ])

        self.layout.addWidget(splitter)

        self.load_products()
        self.load_written_offs()

    def show_context_menu(self, position):
        item = self.product_list.itemAt(position)

        if item is None:
            return

        product_id = item.data(
            0,
            Qt.ItemDataRole.UserRole
        )

        menu = QMenu(self)

        open_action = menu.addAction(
            "Открыть карточку товара"
        )

        menu.addSeparator()

        restore_action = menu.addAction(
            "Восстановить"
        )

        action = menu.exec(
            self.product_list.mapToGlobal(position)
        )

        if action == open_action:
            self.main_window.open_deleted_product(
                product_id
            )

        elif action == restore_action:
            connection = get_connection()
            try:
                connection.execute(
                    """
                    UPDATE products
                    SET deleted = 0
                    WHERE id = ?
                    """,
                    (product_id,)
                )
                connection.commit()
            finally:
                connection.close()

            self.load_products()
            self.main_window.refresh_inventory()
    def show_written_off_context_menu(self, position):
        item = self.written_off_list.itemAt(position)

        if item is None:
            return

        instance_id = item.data(
            0,
            Qt.ItemDataRole.UserRole
        )

        product_id = item.data(
            0,
            Qt.ItemDataRole.UserRole + 1
        )

        menu = QMenu(self)

        open_product_action = menu.addAction(
            "Открыть карточку товара"
        )

        open_instance_action = menu.addAction(
            "Открыть карточку экземпляра"
        )

        action = menu.exec(
            self.written_off_list.mapToGlobal(position)
        )

        if action == open_product_action:
            self.main_window.open_product_card(
                product_id
            )

        elif action == open_instance_action:
            self.main_window.open_instance_card(
                instance_id
            )
    def load_products(self):
        self.product_list.clear()

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT
                    id,
                    manufacturer,
                    part_number,
                    name
                FROM products
                WHERE deleted = 1
                ORDER BY id DESC
                """
            )

            products = cursor.fetchall()

        finally:
            connection.close()

        for (
            product_id,
            manufacturer,
            part_number,
            name,
        ) in products:

            item = QTreeWidgetItem([
                str(product_id),
                manufacturer or "",
                part_number or "",
                name or "",
            ])

            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                product_id
            )

            self.product_list.addTopLevelItem(item)
    def load_written_offs(self):
        self.written_off_list.clear()

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT
                    w.write_off_date,
                    i.internal_number,
                    p.manufacturer,
                    p.part_number,
                    p.name,
                    w.comment,
                    i.id,
                    p.id
                FROM write_offs w
                JOIN instances i
                    ON i.id = w.instance_id
                JOIN products p
                    ON p.id = i.product_id
                WHERE i.status = 'written_off'
                ORDER BY w.write_off_date DESC,
                     i.internal_number DESC
                """
            )

            written_offs = cursor.fetchall()

        finally:
            connection.close()

        for (
            write_off_date,
            internal_number,
            manufacturer,
            part_number,
            name,
            comment,
            instance_id,
            product_id,
        ) in written_offs:

            item = QTreeWidgetItem([
                write_off_date or "",
                f"№{internal_number}",
                manufacturer or "",
                part_number or "",
                name or "",
                comment or "",
            ])

            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                instance_id
            )

            item.setData(
                0,
                Qt.ItemDataRole.UserRole + 1,
                product_id
            )

            self.written_off_list.addTopLevelItem(item)
    def filter_products(self, text):
        text = text.strip().lower()

        for index in range(
            self.product_list.topLevelItemCount()
        ):
            item = self.product_list.topLevelItem(index)

            row_text = " ".join(
                item.text(column)
                for column in range(
                    self.product_list.columnCount()
                )
            ).lower()

            item.setHidden(
                bool(text) and text not in row_text
            )
    def filter_written_offs(self, text):
        text = text.strip().lower()

        for index in range(
            self.written_off_list.topLevelItemCount()
        ):
            item = self.written_off_list.topLevelItem(index)

            row_text = " ".join(
                item.text(column)
                for column in range(
                    self.written_off_list.columnCount()
                )
            ).lower()

            if text:
                item.setHidden(
                    text not in row_text
                )
            else:
                item.setHidden(False)