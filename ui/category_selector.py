from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
)

from database.database import get_connection


class CategorySelector(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        if not hasattr(parent, "_category_tree_state"):
            parent._category_tree_state = {}

        self.tree_state = parent._category_tree_state

        self.setWindowTitle("Выбор категории")
        self.resize(450, 500)

        self.selected_category_id = None
        self.selected_category_name = None

        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Категории")
        self.tree.itemDoubleClicked.connect(
            self.select_category
        )
        layout.addWidget(self.tree)

        select_button = QPushButton("Выбрать")
        select_button.clicked.connect(self.select_category)

        layout.addWidget(select_button)

        self.load_categories()

    def load_categories(self):
        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                SELECT id, name, parent_id
                FROM categories
                ORDER BY name COLLATE NOCASE
                """
            )

            categories = cursor.fetchall()

        finally:
            connection.close()

        self.tree.clear()

        items = {}

        for category_id, name, parent_id in categories:
            item = QTreeWidgetItem([name])

            item.setData(
                0,
                1000,
                category_id
            )

            items[category_id] = item

        for category_id, name, parent_id in categories:
            item = items[category_id]

            if parent_id is None:
                self.tree.addTopLevelItem(item)
            elif parent_id in items:
                items[parent_id].addChild(item)

        def restore_expanded_state(item):
            category_id = item.data(0, 1000)

            item.setExpanded(
                self.tree_state.get(category_id, False)
            )

            for index in range(item.childCount()):
                restore_expanded_state(item.child(index))

        for index in range(self.tree.topLevelItemCount()):
            restore_expanded_state(
                self.tree.topLevelItem(index)
            )

    def select_category(self):
        item = self.tree.currentItem()

        if item is None:
            return

        # Если есть дочерние элементы,
        # это не конечная категория.
        if item.childCount() > 0:
            return

        self.selected_category_id = item.data(
            0,
            1000
        )

        self.selected_category_name = item.text(0)

        self.save_expanded_state()
        self.accept()
    def save_expanded_state(self):
        def save_item_state(item):
            category_id = item.data(0, 1000)

            self.tree_state[category_id] = item.isExpanded()

            for index in range(item.childCount()):
                save_item_state(item.child(index))

        for index in range(self.tree.topLevelItemCount()):
            save_item_state(
                self.tree.topLevelItem(index)
            )

    def closeEvent(self, event):
        self.save_expanded_state()
        super().closeEvent(event)