from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QMessageBox,
    QInputDialog,
    QApplication
)

from models.purchase import (
    get_purchases,
    get_purchase_items,
)


class PurchasesJournal(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.installEventFilter(self)
        self.tree.setContextMenuPolicy(
            Qt.CustomContextMenu
        )

        self.tree.customContextMenuRequested.connect(
            self.show_context_menu
        )

        self.tree.setHeaderLabels([
            "Закупка / экземпляр",
            "Дата",
            "Товар",
            "Артикул",
            "Стоимость",
            "Доставка",
            "Статус",
        ])

        layout.addWidget(self.tree)
        self.tree.setColumnHidden(7, True)
        self.load_purchases()

    def load_purchases(self):
        expanded_numbers = set()

        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)

            if item.isExpanded():
                expanded_numbers.add(item.text(0))

        self.tree.clear()

        purchases = get_purchases()

        for purchase in purchases:
            purchase_id = purchase[0]
            purchase_number = purchase[1]
            purchase_date = purchase[2]
            total_price = purchase[3]
            total_shipping = purchase[4]

            purchase_item = QTreeWidgetItem([
                f"Закупка №{purchase_number:05d}",
                purchase_date,
                "",
                "",
                str(total_price),
                str(total_shipping),
                "",
            ])
            purchase_item.setData(
                0,
                Qt.ItemDataRole.UserRole + 3,
                purchase_id
            )
            purchase_item.setText(
                7,
                str(purchase_id)
            )

            self.tree.addTopLevelItem(purchase_item)

            items = get_purchase_items(purchase_id)

            status_names = {
                "in_stock": "На складе",
                "sold": "Продан",
                "written_off": "Списан",
            }

            for item in items:
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

                product_text = " | ".join(
                    part
                    for part in [
                        manufacturer,
                        name,
                    ]
                    if part
                )

                child = QTreeWidgetItem([
                    f"Экземпляр №{internal_number}",
                    purchase_date,
                    product_text,
                    part_number or "",
                    str(allocated_price),
                    str(allocated_shipping),
                    status_names.get(status, status),
                ])
                child.setData(
                    0,
                    Qt.ItemDataRole.UserRole + 1,
                    instance_id
                )

                child.setData(
                    0,
                    Qt.ItemDataRole.UserRole + 2,
                    product_id
                )
                if write_off_comment:
                    child.setToolTip(
                        6,
                        f"Причина списания:\n{write_off_comment}"
                    )

                child.setText(
                    7,
                    str(instance_id)
                )

                purchase_item.addChild(child)

            purchase_item.setExpanded(
                purchase_item.text(0) in expanded_numbers
            )

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
                if not self.tree.isColumnHidden(column)
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

        menu = QMenu(self)

        # Верхняя строка — сама закупка
        if item.parent() is None:
            purchase_id = item.data(
                0,
                Qt.ItemDataRole.UserRole + 3
            )

            if purchase_id is None:
                return

            open_purchase_action = menu.addAction(
                "Открыть закупку"
            )

            edit_purchase_action = menu.addAction(
                "Редактировать закупку"
            )

            action = menu.exec(
                self.tree.viewport().mapToGlobal(position)
            )

            if action == open_purchase_action:
                self.main_window.open_purchase(
                    int(purchase_id),
                    read_only=True
                )
            elif action == edit_purchase_action:
                self.main_window.open_purchase(
                    int(purchase_id),
                    read_only=False
                )

            return

        # Дочерняя строка — экземпляр
        instance_id = item.data(
            0,
            Qt.ItemDataRole.UserRole + 1
        )

        product_id = item.data(
            0,
            Qt.ItemDataRole.UserRole + 2
        )

        if instance_id is None or product_id is None:
            return

        status = item.text(6)

        product_action = menu.addAction(
            "Открыть карточку товара"
        )
        product_action.triggered.connect(
            lambda: self.main_window.open_product_card(
                int(product_id),
                allow_deleted=True
            )
        )

        instance_action = menu.addAction(
            "Открыть карточку экземпляра"
        )
        instance_action.triggered.connect(
            lambda: self.main_window.open_instance_card(
                int(instance_id)
            )
        )

        menu.addSeparator()

        write_off_action = menu.addAction(
            "Списать экземпляр"
        )

        if status in ("Продан", "Списан"):
            write_off_action.setEnabled(False)

        action = menu.exec(
            self.tree.viewport().mapToGlobal(position)
        )

        if action == write_off_action:
            comment, ok = QInputDialog.getText(
                self,
                "Списание экземпляра",
                "Причина списания:"
            )

            if not ok:
                return

            comment = comment.strip()

            if not comment:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Причина списания обязательна."
                )
                return

            from models.instance import write_off_instance

            try:
                write_off_instance(
                    int(instance_id),
                    comment
                )

                self.load_purchases()

            except Exception as error:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    str(error)
                )