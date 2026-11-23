from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor, QBrush
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

        # Сохранение ширины столбцов журнала закупок
        self.header_settings = QSettings(
            "ARIS",
            "PurchasesJournal"
        )

        header_state = self.header_settings.value(
            "tree_header_state"
        )

        if header_state is not None:
            self.tree.header().restoreState(
                header_state
            )

        self.tree.header().sectionResized.connect(
            self.save_header_state
        )

        self.load_purchases()
    def save_header_state(self, *args):
        self.header_settings.setValue(
            "tree_header_state",
            self.tree.header().saveState()
        )
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

            total_profit = sum(
                item[12] or 0
                for item in items
            )

            total_cost = total_price + total_shipping

            all_sold = (
                len(items) > 0
                and all(item[9] == "sold" for item in items)
            )

            if all_sold:
                green = QBrush(QColor("#A8D5A2"))

            elif total_profit > total_cost:
                green = QBrush(QColor(220, 245, 220))

            else:
                green = None

            if green is not None:
                for column in range(self.tree.columnCount()):
                    purchase_item.setBackground(column, green)

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
                    listed_date,
                    write_off_comment,
                    sale_profit,
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
                if status == "sold":
                    light_green = QBrush(QColor("#DDF0DD"))

                    for column in range(self.tree.columnCount()):
                        child.setBackground(column, light_green)

                elif status == "written_off":
                    light_red = QBrush(QColor("#E6A0A0"))

                    for column in range(self.tree.columnCount()):
                        child.setBackground(column, light_red)

                elif listed_date:
                    yellow = QBrush(QColor("#FFF2CC"))

                    for column in range(self.tree.columnCount()):
                        child.setBackground(column, yellow)
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