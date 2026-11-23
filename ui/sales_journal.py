from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QApplication,
    QMenu
)


class SalesJournal(QWidget):

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout()

        # Левая часть — продажи
        left_layout = QVBoxLayout()

        sales_title = QLabel("Продажи")
        sales_title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        self.sales_table = QTreeWidget()

        self.sales_table.setColumnCount(7)

        self.sales_table.setHeaderLabels([
            "№",
            "Дата",
            "Сумма",
            "Комментарий",
            "Тип",
            "Статус",
            "ID"
        ])

        self.sales_table.setColumnHidden(6, True)

        self.sales_table.setContextMenuPolicy(
            Qt.CustomContextMenu
        )

        self.sales_table.customContextMenuRequested.connect(
            self.show_context_menu
        )
        self.sales_table.installEventFilter(self)
        self.expanded_sales = set()

        left_layout.addWidget(
            sales_title
        )

        left_layout.addWidget(
            self.sales_table
        )

        # Правая часть — возвраты
        right_layout = QVBoxLayout()

        returns_title = QLabel("Возвраты")
        returns_title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        self.returns_table = QTreeWidget()

        self.returns_table.setColumnCount(6)

        self.returns_table.setHeaderLabels([
            "Дата",
            "№ экземпляра",
            "Производитель",
            "Артикул",
            "Название",
            "Причина возврата"
        ])
        self.returns_table.installEventFilter(self)
        right_layout.addWidget(
            returns_title
        )

        right_layout.addWidget(
            self.returns_table
        )

        # Разделитель
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        splitter.setSizes([
            600,
            600
        ])

        layout.addWidget(
            splitter
        )

        self.setLayout(
            layout
        )

        # Сохранение ширины столбцов журнала продаж
        self.sales_header_settings = QSettings(
            "ARIS",
            "SalesJournal"
        )

        sales_header_state = self.sales_header_settings.value(
            "sales_header_state"
        )

        if sales_header_state is not None:
            self.sales_table.header().restoreState(
                sales_header_state
            )

        self.sales_table.header().sectionResized.connect(
            self.save_sales_header_state
        )

        # Сохранение ширины столбцов возвратов
        self.returns_header_settings = QSettings(
            "ARIS",
            "SalesJournal"
        )

        returns_header_state = self.returns_header_settings.value(
            "returns_header_state"
        )

        if returns_header_state is not None:
            self.returns_table.header().restoreState(
                returns_header_state
            )

        self.returns_table.header().sectionResized.connect(
            self.save_returns_header_state
        )

        self.load_sales()
        self.load_returns()
    def save_sales_header_state(self, *args):
        self.sales_header_settings.setValue(
            "sales_header_state",
            self.sales_table.header().saveState()
        )

    def save_returns_header_state(self, *args):
        self.returns_header_settings.setValue(
            "returns_header_state",
            self.returns_table.header().saveState()
        )
    def save_expanded_state(self):
        self.expanded_sales.clear()

        for i in range(
            self.sales_table.topLevelItemCount()
        ):
            item = self.sales_table.topLevelItem(i)

            if item.isExpanded():
                sale_id = item.text(6)

                self.expanded_sales.add(
                    int(sale_id)
                )


    def restore_expanded_state(self):
        for i in range(
            self.sales_table.topLevelItemCount()
        ):
            item = self.sales_table.topLevelItem(i)

            sale_id = int(
                item.text(6)
            )

            item.setExpanded(
                sale_id in self.expanded_sales
            )
    def load_sales(self):
        self.save_expanded_state()
        from models.sale import get_sales

        sales = get_sales()

        self.sales_table.clear()

        self.sales_table.setColumnCount(7)
        self.sales_table.setColumnHidden(6, True)

        self.sales_table.setHeaderLabels([
            "№",
            "Дата",
            "Сумма",
            "Комментарий",
            "Тип",
            "Статус",
            "ID"
        ])

        for sale in sales:
            item = QTreeWidgetItem([
                str(sale[1]),
                sale[2],
                str(sale[3]),
                sale[4] or "",
                "Продажа",
                "Завершена"
            ])

            item.setText(
                6,
                str(sale[0])
            )

            self.sales_table.addTopLevelItem(
                item
            )

            from models.sale import (
                get_sale_items_for_journal
            )

            sale_items = get_sale_items_for_journal(
                sale[0]
            )

            for sale_item in sale_items:
                status = (
                    "Продано"
                    if sale_item[11]
                    else "Возврат"
                )

                child = QTreeWidgetItem([
                    f"№{sale_item[2]}",
                    sale_item[3] or "",
                    str(sale_item[6]),
                    (
                        f"{sale_item[4] or ''} — {sale_item[5] or ''}"
                        if sale_item[4]
                        else sale_item[5] or ""
                    ),
                    "Экземпляр",
                    status
                ])

                child.setText(
                    6,
                    str(sale_item[1])
                )

                item.addChild(
                    child
                )
        self.restore_expanded_state()

    def load_returns(self):
        from models.sale import get_returns

        returns = get_returns()

        self.returns_table.clear()

        for return_item in returns:
            item = QTreeWidgetItem([
                return_item[0],
                f"№{return_item[1]}",
                return_item[2] or "",
                return_item[3] or "",
                return_item[4] or "",
                return_item[5] or ""
            ])

            self.returns_table.addTopLevelItem(
                item
            )

    def eventFilter(self, obj, event):
        if (
            obj in (
                self.sales_table,
                self.returns_table
            )
            and event.type() == event.Type.KeyPress
            and event.key() == Qt.Key_C
            and event.modifiers() & Qt.ControlModifier
        ):
            item = obj.currentItem()

            if item is None:
                return True

            values = []

            for column in range(obj.columnCount()):
                if obj.isColumnHidden(column):
                    continue

                values.append(
                    item.text(column)
                )

            QApplication.clipboard().setText(
                "\t".join(values)
            )

            return True

        return super().eventFilter(obj, event)

    def show_context_menu(self, position):
        item = self.sales_table.itemAt(position)

        if item is None:
            return

        menu = QMenu(self)

        # ПКМ по продаже
        if item.parent() is None:
            sale_id = int(
                item.text(6)
            )

            open_action = menu.addAction(
                "Открыть продажу"
            )

            edit_action = menu.addAction(
                "Редактировать продажу"
            )

            action = menu.exec(
                self.sales_table.viewport().mapToGlobal(
                    position
                )
            )

            window = self.window()

            if action == open_action:
                if hasattr(
                    window,
                    "open_sale"
                ):
                    window.open_sale(
                        sale_id
                    )

            elif action == edit_action:
                if hasattr(
                    window,
                    "open_sale"
                ):
                    window.open_sale(
                        sale_id,
                        edit_mode=True
                    )

            return

        # ПКМ по экземпляру
        instance_id = int(
            item.text(6)
        )
        open_product_action = menu.addAction(
            "Открыть карточку товара"
        )
        open_instance_action = menu.addAction(
            "Открыть карточку экземпляра"
        )

        return_action = menu.addAction(
            "Вернуть товар"
        )

        if item.text(5) == "Возврат":
            return_action.setEnabled(False)

        action = menu.exec(
            self.sales_table.viewport().mapToGlobal(
                position
            )
        )

        if action == open_product_action:
            from models.instance import get_instance

            instance = get_instance(
                instance_id
            )

            if instance is None:
                return

            product_id = instance[2]

            window = self.window()

            if hasattr(
                window,
                "open_product_card"
            ):
                window.open_product_card(
                    product_id,
                    allow_deleted=True
                )

        elif action == open_instance_action:
            window = self.window()

            if hasattr(
                window,
                "open_instance_card"
            ):
                window.open_instance_card(
                    instance_id
                )

        elif action == return_action:
            self.return_instance(
                item
            )

    def return_instance(self, item):
        from PySide6.QtWidgets import QInputDialog

        instance_id = int(
            item.text(6)
        )

        answer = QMessageBox.question(
            self,
            "Возврат",
            "Вернуть этот экземпляр?"
        )

        if answer != QMessageBox.Yes:
            return

        comment, ok = QInputDialog.getText(
            self,
            "Причина возврата",
            "Укажите причину возврата:"
        )

        if not ok:
            return

        comment = comment.strip()

        if not comment:
            QMessageBox.warning(
                self,
                "Причина возврата",
                "Причина возврата обязательна."
            )
            return

        from models.sale import return_sale_item

        sale_id = int(
            item.parent().text(6)
        )

        try:
            return_sale_item(
                sale_id,
                instance_id,
                comment
            )

            self.load_sales()

            QMessageBox.information(
                self,
                "Возврат",
                "Экземпляр возвращён на склад."
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка",
                str(error)
            )