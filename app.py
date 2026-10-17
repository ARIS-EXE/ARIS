import sys

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QTabWidget,
    QTabBar,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFrame,
    QMessageBox,
    QFileDialog,
)

from database.database import initialize_database
from ui.product_card import ProductCard
from ui.instance_card import InstanceCard
from ui.inventory import Inventory
from ui.categories import Categories
from ui.sale_card import SaleCard
from ui.purchase_card import PurchaseCard
from ui.purchases_journal import PurchasesJournal
from ui.trash import Trash
from ui.dashboard import Dashboard
from backup.backup_settings_dialog import BackupSettingsDialog
from backup.backup_manager import create_automatic_backup
from ui.settings import SettingsDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ARIS - Управление товарами, закупками и продажами")

        try:
            create_automatic_backup()
        except Exception as error:
            print(
                f"Automatic backup error: {error}"
            )

        self.resize(1200, 750)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.setTabsClosable(True)

        self.tab_history = []

        self.tabs.tabCloseRequested.connect(
            self.close_tab
        )
        self.tabs.currentChanged.connect(
            self.refresh_current_tab
        )
        # Главная
        main_tab = QWidget()
        main_layout = QHBoxLayout(main_tab)

        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        title = QLabel("RC Inventory")
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold;"
        )

        left_layout.addWidget(title)

        new_product_button = QPushButton(
            "+ Новый товар"
        )
        new_product_button.setFixedWidth(180)
        new_product_button.clicked.connect(
            self.open_new_product
        )

        new_sale_button = QPushButton(
            "+ Продажа"
        )
        new_sale_button.setFixedWidth(180)
        new_sale_button.clicked.connect(
            self.open_new_sale
        )
        new_purchase_button = QPushButton(
            "+ Закупка"
        )
        new_purchase_button.setFixedWidth(180)
        new_purchase_button.clicked.connect(
            self.open_new_purchase
        )
        left_layout.addWidget(new_product_button)
        left_layout.addWidget(new_sale_button)
        left_layout.addWidget(new_purchase_button)

        left_layout.addStretch(1)

        sections_label = QLabel("Разделы")
        left_layout.addWidget(sections_label)

        inventory_button = QPushButton("Склад")
        categories_button = QPushButton("Категории")
        sales_journal_button = QPushButton("Журнал продаж")
        purchases_journal_button = QPushButton("Журнал закупок")
        deleted_button = QPushButton("Корзина")
        inventory_button.clicked.connect(self.open_inventory)
        categories_button.clicked.connect(self.open_categories)
        sales_journal_button.clicked.connect(self.open_sales_journal)
        purchases_journal_button.clicked.connect(self.open_purchases_journal)
        deleted_button.clicked.connect(self.open_deleted)
        inventory_button.setFixedWidth(180)
        categories_button.setFixedWidth(180)
        sales_journal_button.setFixedWidth(180)
        purchases_journal_button.setFixedWidth(180)
        deleted_button.setFixedWidth(180)

        left_layout.addWidget(inventory_button)
        left_layout.addWidget(categories_button)
        left_layout.addWidget(sales_journal_button)
        left_layout.addWidget(purchases_journal_button)
        left_layout.addWidget(deleted_button)

        left_layout.addStretch(1)


        settings_button = QPushButton("Настройки")
        settings_button.setFixedWidth(180)
        settings_button.clicked.connect(
            self.open_settings
        )

        left_layout.addWidget(settings_button)


        main_layout.addLayout(left_layout, 0)
        self.dashboard = Dashboard()
        right_layout.addWidget(self.dashboard)

        version_label = QLabel(
            "Версия 1.0  Prod. by Iev37"
        )
        version_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        version_label.setStyleSheet(
            "color: #999999; font-size: 11px;"
        )

        right_layout.addWidget(version_label)

        main_layout.addLayout(right_layout, 1)
        self.tabs.addTab(main_tab, "Главная")
        self.tabs.tabBar().setTabButton(
            0,
            QTabBar.RightSide,
            None
        )

    def open_product_card(
        self,
        product_id,
        allow_deleted=False
    ):
        # Если карточка уже открыта — просто переключаемся на неё.
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)

            if (
                isinstance(widget, ProductCard)
                and widget.product_id == product_id
                and widget.allow_deleted == allow_deleted
            ):
                self.tabs.setCurrentIndex(index)
                return

        # Карточка ещё не открыта — создаём новую вкладку.
        product_tab = ProductCard(
            product_id,
            allow_deleted=allow_deleted
        )

        tab_title = product_tab.name.text().strip()

        if not tab_title:
            tab_title = "Карточка товара"

        tab_index = self.tabs.addTab(
            product_tab,
            tab_title
        )

        self.tabs.setCurrentIndex(tab_index)

        product_tab.destroyed.connect(
            self.refresh_inventory
        )
    def open_deleted_product(self, product_id):
        self.open_product_card(
            product_id,
            allow_deleted=True
        )

    def open_sale(
        self,
        sale_id,
        edit_mode=False
    ):
        sale_tab = SaleCard(
            sale_id,
            edit_mode,
            self
        )

        sale_number = "Продажа"

        if sale_id is not None:
            from models.sale import get_sale

            sale = get_sale(
                sale_id
            )

            if sale is not None:
                sale_number = (
                    f"Продажа №{sale[1]:05d}"
                )

                if edit_mode:
                    sale_number = (
                        f"Редактирование продажи №{sale[1]:05d}"
                    )

        tab_index = self.tabs.addTab(
            sale_tab,
            sale_number
        )

        self.tabs.setCurrentIndex(
            tab_index
        )

    def open_new_sale(self):
        sale_tab = SaleCard(
            main_window=self
        )

        tab_index = self.tabs.addTab(
            sale_tab,
            "Новая продажа"
        )

        self.tabs.setCurrentIndex(
            tab_index
        )
    def open_new_purchase(self):
        purchase_tab = PurchaseCard(self)

        tab_index = self.tabs.addTab(
            purchase_tab,
            "Новая закупка"
        )

        self.tabs.setCurrentIndex(
            tab_index
        )



    def open_purchase(self, purchase_id, read_only=False):
        purchase_tab = PurchaseCard(
            self,
            purchase_id=purchase_id,
            read_only=read_only
        )

        title = (
            "Просмотр закупки"
            if read_only
            else "Редактирование закупки"
        )

        tab_index = self.tabs.addTab(
            purchase_tab,
            title
        )

        self.tabs.setCurrentIndex(tab_index)

    def open_purchase_for_instance(self, instance_id):
        from models.instance import get_instance

        instance = get_instance(instance_id)

        if instance is None or instance[9]:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Экземпляр не найден или удалён."
            )
            return

        purchase_tab = PurchaseCard(self)
        purchase_tab.add_instance_to_purchase(instance_id)

        tab_index = self.tabs.addTab(
            purchase_tab,
            "Новая закупка"
        )

        self.tabs.setCurrentIndex(tab_index)

    def add_placeholder_tab(self, name):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        label = QLabel(f"Раздел «{name}»")
        label.setStyleSheet("font-size: 22px;")

        layout.addWidget(label)
        layout.addStretch()

        self.tabs.addTab(tab, name)

    def open_instance_card(self, instance_id):
        # Если карточка экземпляра уже открыта —
        # просто переключаемся на неё.
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)

            if (
                isinstance(widget, InstanceCard)
                and widget.instance_id == instance_id
            ):
                self.tabs.setCurrentIndex(index)
                return

        # Карточка ещё не открыта — создаём новую вкладку.
        instance_tab = InstanceCard(instance_id)

        instance_number = (
            instance_tab.internal_number.text().strip()
        )

        if instance_number:
            tab_title = f"Экземпляр №{instance_number}"
        else:
            tab_title = "Экземпляр"

        tab_index = self.tabs.addTab(
            instance_tab,
            tab_title
        )

        self.tabs.setCurrentIndex(tab_index)

    def open_new_product(self):
        current_widget = self.tabs.currentWidget()

        if current_widget is not None:
            if current_widget in self.tab_history:
                self.tab_history.remove(current_widget)

            self.tab_history.append(current_widget)

        product_tab = ProductCard()

        tab_index = self.tabs.addTab(
            product_tab,
            "Новый товар"
        )

        self.tabs.setCurrentIndex(tab_index)

        product_tab.destroyed.connect(
            self.refresh_inventory
        )

    def create_backup(self):
        from backup.backup_manager import create_backup

        try:
            backup_path = create_backup()

            QMessageBox.information(
                self,
                "Резервное копирование",
                f"Резервная копия создана:\n\n{backup_path}"
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось создать резервную копию:\n\n{error}"
            )

    def open_backup_settings(self):
        dialog = BackupSettingsDialog(self)
        dialog.exec()

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def restore_backup(self):
        from backup.backup_manager import restore_backup

        backup_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите резервную копию",
            "",
            "Резервные копии (*.zip)"
        )

        if not backup_path:
            return

        answer = QMessageBox.question(
            self,
            "Восстановление",
            "Восстановить данные из выбранной резервной копии?\n\n"
            "Текущее состояние перед восстановлением "
            "будет автоматически сохранено.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if answer != QMessageBox.Yes:
            return

        try:
            restore_backup(backup_path)

            QMessageBox.information(
                self,
                "Восстановление",
                "Данные успешно восстановлены.\n\n"
                "Для полного применения изменений "
                "перезапустите программу."
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось восстановить резервную копию:\n\n{error}"
            )

    def close_tab(self, index):
        if index == 0:
            return

        current_widget = self.tabs.widget(index)

        # Удаляем закрываемую вкладку из истории
        if current_widget in self.tab_history:
            self.tab_history.remove(current_widget)

        # Находим последнюю открытую вкладку из истории
        previous_widget = None

        for widget in reversed(self.tab_history):
            if self.tabs.indexOf(widget) >= 0:
                previous_widget = widget
                break

        # Закрываем вкладку
        self.tabs.removeTab(index)

        # Активируем последнюю вкладку из истории
        if previous_widget is not None:
            previous_index = self.tabs.indexOf(
                previous_widget
            )

            if previous_index >= 0:
                self.tabs.setCurrentIndex(
                    previous_index
                )
    def open_section(self, title, widget_factory):
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == title:
                self.tabs.setCurrentIndex(index)
                return

        tab = widget_factory()
        index = self.tabs.addTab(tab, title)
        self.tabs.setCurrentIndex(index)
    def open_inventory(self):
        self.open_section(
            "Склад",
            lambda: Inventory(self)
        )
    def open_inventory_by_category(self, category_id):
        self.open_inventory()

        widget = self.tabs.currentWidget()

        if isinstance(widget, Inventory):
            widget.category_filter_id = category_id
            widget.load_products()
    def open_categories(self):
        self.open_section(
            "Категории",
            Categories
        )
    def open_sales_journal(self):
        from ui.sales_journal import SalesJournal

        self.open_section(
            "Журнал продаж",
            SalesJournal
        )
    def open_purchases_journal(self):
        self.open_section(
            "Журнал закупок",
            lambda: PurchasesJournal(self)
        )
    def open_deleted(self):
        self.open_section(
            "Корзина",
            lambda: Trash(self)
        )
    def refresh_inventory(self):
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)

            if isinstance(widget, Inventory):
                widget.load_products()
                return
    def refresh_current_tab(self, index):
        widget = self.tabs.widget(index)

        if index == 0:
            self.dashboard.refresh()
        if isinstance(widget, InstanceCard):
            widget.load_instance()

        elif isinstance(widget, Inventory):
            widget.restore_expanded_state()

        elif hasattr(widget, "load_purchases"):
            widget.load_purchases()

        elif hasattr(widget, "load_sales"):
            widget.load_sales()

            if hasattr(widget, "load_returns"):
                widget.load_returns()

        elif hasattr(widget, "load_products"):
            widget.load_products()

        if widget is not None:
            if widget in self.tab_history:
                self.tab_history.remove(widget)

            self.tab_history.append(widget)

initialize_database()

app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())