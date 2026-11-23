from PySide6.QtWidgets import QMenu, QInputDialog, QMessageBox

from models.instance import write_off_instance
from models.purchase import get_purchase_id_by_instance
from models.sale import get_sale_id_by_instance



def show_instance_menu(
    parent,
    global_position,
    main_window,
    instance_id,
    product_id=None,
    status=None,
    show_product_action=True
):
    menu = QMenu(parent)

    if show_product_action and product_id is not None:
        add_open_product_action(
            menu,
            main_window,
            product_id
        )

    add_open_instance_action(
        menu,
        main_window,
        instance_id
    )

    menu.addSeparator()

    add_purchase_instance_action(
        menu,
        main_window,
        instance_id,
        status
    )

    add_sell_instance_action(
        menu,
        main_window,
        instance_id,
        status
    )

    add_open_sale_action(
        menu,
        main_window,
        instance_id,
        status
    )
    add_write_off_action(
        menu=menu,
        parent=parent,
        instance_id=instance_id,
        status=status,
        on_success=lambda: main_window.refresh_current_tab(
            main_window.tabs.currentIndex()
        )
    )
    menu.exec(global_position)

def add_open_product_action(
    menu,
    main_window,
    product_id,
    allow_deleted=False
):
    action = menu.addAction("Открыть карточку товара")
    action.triggered.connect(
        lambda: main_window.open_product_card(
            int(product_id),
            allow_deleted=allow_deleted
        )
    )
    return action

def add_open_instance_action(menu, main_window, instance_id):
    action = menu.addAction("Открыть карточку экземпляра")

    action.triggered.connect(
        lambda: main_window.open_instance_card(int(instance_id))
    )

    return action
def write_off_instance_with_dialog(
    parent,
    instance_id,
    on_success=None
):
    comment, ok = QInputDialog.getText(
        parent,
        "Списание экземпляра",
        "Причина списания:"
    )

    if not ok:
        return False

    comment = comment.strip()

    if not comment:
        QMessageBox.warning(
            parent,
            "Ошибка",
            "Причина списания обязательна."
        )
        return False

    try:
        write_off_instance(
            int(instance_id),
            comment
        )

    except Exception as error:
        QMessageBox.warning(
            parent,
            "Ошибка",
            str(error)
        )
        return False

    if on_success is not None:
        on_success()

    return True


def add_write_off_action(
    menu,
    parent,
    instance_id,
    status,
    on_success=None
):
    if status != "in_stock":
        return None

    action = menu.addAction(
        "Списать экземпляр"
    )

    action.triggered.connect(
        lambda: write_off_instance_with_dialog(
            parent,
            instance_id,
            on_success
        )
    )

    return action
def add_sell_instance_action(
    menu,
    main_window,
    instance_id,
    status
):
    if status != "in_stock":
        return None

    action = menu.addAction("Продать")

    action.triggered.connect(
        lambda: main_window.sell_instance(
            int(instance_id)
        )
    )

    return action


def add_open_sale_action(
    menu,
    main_window,
    instance_id,
    status
):
    if status != "sold":
        return None

    sale_id = get_sale_id_by_instance(instance_id)

    if sale_id is None:
        return None

    action = menu.addAction(
        "Открыть документ продажи"
    )

    action.triggered.connect(
        lambda: main_window.open_sale(
            int(sale_id)
        )
    )

    return action

def add_purchase_instance_action(menu, main_window, instance_id, status):
    if status not in ("in_stock", "sold", "written_off"):
        return None

    purchase_id = get_purchase_id_by_instance(instance_id)

    if purchase_id is not None:
        action = menu.addAction("Открыть документ закупки")
        action.triggered.connect(
            lambda: main_window.open_purchase(int(purchase_id))
        )
    else:
        action = menu.addAction("Закупить")
        action.triggered.connect(
            lambda: main_window.open_purchase_for_instance(
                int(instance_id)
            )
        )

    return action

def add_open_purchase_action(menu, main_window, instance_id):
    purchase_id = get_purchase_id_by_instance(instance_id)

    if purchase_id is None:
        return None

    action = menu.addAction("Открыть документ закупки")
    action.triggered.connect(
        lambda: main_window.open_purchase(int(purchase_id))
    )

    return action

def add_open_purchase_by_id_action(menu, main_window, purchase_id):
    if purchase_id is None:
        return None

    action = menu.addAction("Открыть закупку")
    action.triggered.connect(
        lambda: main_window.open_purchase(int(purchase_id))
    )
    return action


def add_open_sale_by_id_action(menu, main_window, sale_id):
    if sale_id is None:
        return None

    action = menu.addAction("Открыть продажу")
    action.triggered.connect(
        lambda: main_window.open_sale(int(sale_id))
    )
    return action