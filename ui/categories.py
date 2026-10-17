from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QInputDialog,
    QMenu,
)

from database.database import get_connection


class Categories(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)

        title = QLabel("Категории")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        main_layout.addWidget(title)

        input_layout = QHBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(
            "Название категории"
        )

        add_button = QPushButton("Добавить")
        add_button.clicked.connect(
            self.add_category
        )

        input_layout.addWidget(self.name_input)
        input_layout.addWidget(add_button)

        main_layout.addLayout(input_layout)

        self.tree = QTreeWidget()
        self.tree.installEventFilter(self)
        self.tree.setContextMenuPolicy(
            Qt.CustomContextMenu
        )

        self.tree.customContextMenuRequested.connect(
            self.show_context_menu
        )
        self.tree.setHeaderLabel("Категории")

        main_layout.addWidget(self.tree)

        self.load_categories()
    def eventFilter(self, obj, event):
        if (
            obj is self.tree
            and event.type() == event.Type.KeyPress
            and event.key() == Qt.Key.Key_C
            and event.modifiers()
            & Qt.KeyboardModifier.ControlModifier
        ):
            item = self.tree.currentItem()

            if item is not None:
                QApplication.clipboard().setText(
                    item.text(0)
                )
                return True

        return super().eventFilter(obj, event)
    def load_categories(self):
        expanded_categories = set()

        def collect_expanded(item):
            if item.isExpanded():
                expanded_categories.add(
                    item.data(0, 1000)
                )

            for index in range(item.childCount()):
                collect_expanded(item.child(index))

        for index in range(self.tree.topLevelItemCount()):
            collect_expanded(
                self.tree.topLevelItem(index)
            )

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

            else:
                self.tree.addTopLevelItem(item)

        for category_id, item in items.items():
            item.setExpanded(
                category_id in expanded_categories
            )
    def add_subcategory(self, parent_item):
        name, ok = QInputDialog.getText(
            self,
            "Добавить подкатегорию",
            "Название:"
        )

        if not ok:
            return

        name = name.strip()

        if not name:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Название категории не может быть пустым."
            )
            return

        parent_id = parent_item.data(
            0,
            1000
        )

        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT INTO categories (
                    name,
                    parent_id
                )
                VALUES (?, ?)
                """,
                (
                    name,
                    parent_id
                )
            )

            connection.commit()

        except Exception as error:
            connection.rollback()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось добавить подкатегорию:\n\n{error}"
            )

            return

        finally:
            connection.close()

        self.load_categories()
    def show_context_menu(self, position):
        item = self.tree.itemAt(position)

        if item is None:
            return

        menu = QMenu(self)

        add_action = menu.addAction(
            "Добавить подкатегорию"
        )

        rename_action = menu.addAction(
            "Переименовать"
        )

        delete_action = menu.addAction(
            "Удалить"
        )
        view_products_action = menu.addAction(
            "Просмотреть список товаров"
        )
        action = menu.exec(
            self.tree.viewport().mapToGlobal(position)
        )

        if action == add_action:
            self.add_subcategory(item)

        elif action == rename_action:
            self.rename_category(item, 0)

        elif action == delete_action:
            self.delete_category(item)
        elif action == view_products_action:
            category_id = item.data(0, 1000)

            self.window().open_inventory_by_category(
                category_id
            )
    def add_category(self):
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Введите название категории."
            )
            return

        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT INTO categories (
                    name,
                    parent_id
                )
                VALUES (?, NULL)
                """,
                (name,)
            )

            connection.commit()

        except Exception as error:
            connection.rollback()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось добавить категорию:\n\n{error}"
            )

            return

        finally:
            connection.close()

        self.name_input.clear()
        self.load_categories()

    def rename_category(self, item, column):
       category_id = item.data(
           0,
           1000
       )

       old_name = item.text(0)

       new_name, ok = QInputDialog.getText(
           self,
           "Переименовать категорию",
           "Новое название:",
           text=old_name
       )

       if not ok:
           return

       new_name = new_name.strip()

       if not new_name:
           QMessageBox.warning(
               self,
               "Ошибка",
               "Название категории не может быть пустым."
           )
           return

       if new_name == old_name:
           return

       connection = get_connection()

       try:
           connection.execute(
               """
               UPDATE categories
               SET name = ?
               WHERE id = ?
               """,
               (
                   new_name,
                   category_id
               )
           )

           connection.commit()

       except Exception as error:
           connection.rollback()

           QMessageBox.critical(
               self,
               "Ошибка",
               f"Не удалось переименовать категорию:\n\n{error}"
           )

           return

       finally:
           connection.close()

       self.load_categories()

    def delete_category(self, item=None):
       selected_item = item

       if selected_item is None:
           return

       category_id = selected_item.data(
           0,
           1000
       )

       category_name = selected_item.text(0)
       category_id = selected_item.data(
           0,
           1000
       )

       category_name = selected_item.text(0)

       connection = get_connection()

       try:
           # Проверяем подкатегории
           cursor = connection.execute(
               """
               SELECT COUNT(*)
               FROM categories
               WHERE parent_id = ?
               """,
               (category_id,)
           )

           children_count = cursor.fetchone()[0]

           if children_count > 0:
               QMessageBox.warning(
                   self,
                   "Нельзя удалить категорию",
                   "У этой категории есть подкатегории."
               )
               return

           # Проверяем товары
           cursor = connection.execute(
               """
               SELECT COUNT(*)
               FROM products
               WHERE category_id = ?
                 AND deleted = 0
               """,
               (category_id,)
           )

           product_count = cursor.fetchone()[0]

           if product_count > 0:
               QMessageBox.warning(
                   self,
                   "Нельзя удалить категорию",
                   "Эта категория используется товарами."
               )
               return

       finally:
           connection.close()

       answer = QMessageBox.question(
           self,
           "Удаление категории",
           f"Удалить категорию «{category_name}»?",
           QMessageBox.StandardButton.Yes
           | QMessageBox.StandardButton.No
       )

       if answer != QMessageBox.StandardButton.Yes:
           return

       connection = get_connection()

       try:
           connection.execute(
               """
               DELETE FROM categories
               WHERE id = ?
               """,
               (category_id,)
           )

           connection.commit()

       except Exception as error:
           connection.rollback()

           QMessageBox.critical(
               self,
               "Ошибка",
               f"Не удалось удалить категорию:\n\n{error}"
           )

           return

       finally:
           connection.close()

       self.load_categories()