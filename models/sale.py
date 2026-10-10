from database.database import get_connection
def finalize_sale(
    sale_date,
    comment,
    items
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        sale_number = get_next_sale_number()

        total_buyer_paid = sum(
            item["sale_price"]
            + item["buyer_shipping"]
            for item in items
        )

        cursor.execute(
            """
            INSERT INTO sales (
                sale_number,
                sale_date,
                total_buyer_paid,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                sale_number,
                sale_date,
                total_buyer_paid,
                comment
            )
        )

        sale_id = cursor.lastrowid
        for item in items:
            cursor.execute(
                """
                SELECT purchase_price, purchase_shipping
                FROM instances
                WHERE id = ?
                """,
                (
                    item["instance_id"],
                )
            )

            purchase_price, purchase_shipping = (
                cursor.fetchone()
            )

            profit = (
                item["sale_price"]
                - item["buyer_shipping"]
                - item["packaging"]
                - item["commission"]
                - purchase_price
                - purchase_shipping
            )

            cursor.execute(
                """
                INSERT INTO sale_items (
                    sale_id,
                    instance_id,
                    sale_price,
                    buyer_shipping,
                    packaging,
                    commission,
                    profit
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    item["instance_id"],
                    item["sale_price"],
                    item["buyer_shipping"],
                    item["packaging"],
                    item["commission"],
                    profit
                )
            )
            cursor.execute(
                """
                INSERT INTO events (
                    event_date,
                    event_type,
                    instance_id,
                    sale_id,
                    amount
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    sale_date,
                    "sale",
                    item["instance_id"],
                    sale_id,
                    item["sale_price"]
                )
            )
        for item in items:
            cursor.execute(
                """
                UPDATE instances
                SET status = 'sold'
                WHERE id = ?
                """,
                (
                    item["instance_id"],
                )
            )
        connection.commit()

        return sale_id, sale_number

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def return_sale_item(
    sale_id,
    instance_id,
    comment=""
):
    from datetime import date

    comment = comment.strip()

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM sale_items
            WHERE sale_id = ?
              AND instance_id = ?
              AND active = 1
            """,
            (
                sale_id,
                instance_id
            )
        )

        sale_item = cursor.fetchone()

        if sale_item is None:
            raise ValueError(
                "Активная позиция продажи не найдена."
            )

        cursor.execute(
            """
            UPDATE sale_items
            SET active = 0
            WHERE id = ?
            """,
            (
                sale_item[0],
            )
        )

        cursor.execute(
            """
            UPDATE instances
            SET status = 'in_stock'
            WHERE id = ?
            """,
            (
                instance_id,
            )
        )
        connection.execute(
            """
            INSERT INTO returns (
                instance_id,
                sale_id,
                return_date
            )
            VALUES (?, ?, ?)
            """,
            (
                instance_id,
                sale_id,
                date.today().isoformat()
            )
        )
        connection.execute(
            """
            INSERT INTO events (
                event_date,
                event_type,
                instance_id,
                sale_id,
                comment
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                date.today().isoformat(),
                "return",
                instance_id,
                sale_id,
                comment
            )
        )

        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def get_sales():
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                id,
                sale_number,
                sale_date,
                total_buyer_paid,
                comment
            FROM sales
            ORDER BY sale_number DESC
            """
        )

        return cursor.fetchall()

    finally:
        connection.close()
def update_sale(
    sale_id,
    sale_date,
    comment
):
    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE sales
            SET sale_date = ?,
                comment = ?
            WHERE id = ?
            """,
            (
                sale_date,
                comment,
                sale_id
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def get_sale_items_for_journal(sale_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                sale_items.id,
                sale_items.instance_id,
                instances.internal_number,
                products.manufacturer,
                products.part_number,
                products.name,
                sale_items.sale_price,
                sale_items.buyer_shipping,
                sale_items.packaging,
                sale_items.commission,
                sale_items.profit,
                sale_items.active
            FROM sale_items
            JOIN instances
                ON instances.id = sale_items.instance_id
            JOIN products
                ON products.id = instances.product_id
            WHERE sale_items.sale_id = ?
            ORDER BY sale_items.id
            """,
            (sale_id,)
        )

        return cursor.fetchall()

    finally:
        connection.close()
def get_next_sale_number():
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT MAX(sale_number)
            FROM sales
            """
        )

        result = cursor.fetchone()[0]

        if result is None:
            return 1

        return result + 1

    finally:
        connection.close()
def create_sale(
    sale_date,
    total_buyer_paid=0,
    comment=""
):
    sale_number = get_next_sale_number()

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO sales (
                sale_number,
                sale_date,
                total_buyer_paid,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                sale_number,
                sale_date,
                total_buyer_paid,
                comment
            )
        )

        connection.commit()

        return cursor.lastrowid

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def add_sale_item(
    sale_id,
    instance_id,
    sale_price,
    buyer_shipping=0,
    packaging=0,
    commission=0
):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                purchase_price,
                purchase_shipping,
                status,
                deleted
            FROM instances
            WHERE id = ?
            """,
            (instance_id,)
        )

        instance = cursor.fetchone()

        if instance is None:
            raise ValueError(
                "Экземпляр не найден."
            )

        purchase_price = instance[0] or 0
        purchase_shipping = instance[1] or 0
        status = instance[2]
        deleted = instance[3]

        if deleted:
            raise ValueError(
                "Удалённый экземпляр нельзя продать."
            )

        if status != "in_stock":
            raise ValueError(
                "Продать можно только экземпляр со статусом «В наличии»."
            )
        cursor = connection.execute(
            """
            SELECT id
            FROM sale_items
            WHERE instance_id = ?
              AND active = 1
            """,
            (instance_id,)
        )

        existing_sale_item = cursor.fetchone()

        if existing_sale_item is not None:
            raise ValueError(
                "Этот экземпляр уже добавлен в продажу."
            )
        profit = (
            sale_price
            + buyer_shipping
            - buyer_shipping
            - commission
            - packaging
            - purchase_price
            - purchase_shipping
        )

        connection.execute(
            """
            INSERT INTO sale_items (
                sale_id,
                instance_id,
                sale_price,
                buyer_shipping,
                packaging,
                commission,
                profit,
                active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                sale_id,
                instance_id,
                sale_price,
                buyer_shipping,
                packaging,
                commission,
                profit
            )
        )
        cursor = connection.execute(
            """
            SELECT sale_date
            FROM sales
            WHERE id = ?
            """,
            (sale_id,)
        )

        sale = cursor.fetchone()

        if sale is None:
            raise ValueError(
                "Продажа не найдена."
            )

        connection.execute(
            """
            INSERT INTO events (
                event_date,
                event_type,
                instance_id,
                sale_id,
                amount
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                sale[0],
                "sale",
                instance_id,
                sale_id,
                sale_price
            )
        )
        connection.execute(
            """
            UPDATE instances
            SET status = 'sold'
            WHERE id = ?
            """,
            (instance_id,)
        )
        connection.execute(
            """
            UPDATE sales
            SET total_buyer_paid =
                COALESCE(total_buyer_paid, 0) + ?
            WHERE id = ?
            """,
            (
                sale_price,
                sale_id
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def complete_sale(sale_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT instance_id
            FROM sale_items
            WHERE sale_id = ?
              AND active = 1
            """,
            (sale_id,)
        )

        items = cursor.fetchall()

        if not items:
            raise ValueError(
                "В продаже нет экземпляров."
            )

        for item in items:
            instance_id = item[0]

            connection.execute(
                """
                UPDATE instances
                SET status = 'sold'
                WHERE id = ?
                  AND status = 'in_stock'
                """,
                (instance_id,)
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def cancel_sale(sale_id):
    connection = get_connection()

    try:
        connection.execute(
            """
            DELETE FROM sale_items
            WHERE sale_id = ?
              AND active = 1
            """,
            (sale_id,)
        )

        connection.execute(
            """
            DELETE FROM sales
            WHERE id = ?
            """,
            (sale_id,)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def return_instance(instance_id, sale_id, return_date):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT id
            FROM sale_items
            WHERE instance_id = ?
              AND sale_id = ?
              AND active = 1
            """,
            (
                instance_id,
                sale_id
            )
        )

        sale_item = cursor.fetchone()

        if sale_item is None:
            raise ValueError(
                "Активная продажа этого экземпляра не найдена."
            )

        connection.execute(
            """
            UPDATE sale_items
            SET active = 0
            WHERE id = ?
            """,
            (sale_item[0],)
        )

        connection.execute(
            """
            UPDATE instances
            SET status = 'in_stock'
            WHERE id = ?
            """,
            (instance_id,)
        )

        connection.execute(
            """
            INSERT INTO returns (
                instance_id,
                sale_id,
                return_date
            )
            VALUES (?, ?, ?)
            """,
            (
                instance_id,
                sale_id,
                return_date
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def update_sale_item(
    sale_item_id,
    sale_price,
    buyer_shipping,
    packaging,
    commission
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                instances.purchase_price,
                instances.purchase_shipping
            FROM sale_items
            JOIN instances
                ON instances.id = sale_items.instance_id
            WHERE sale_items.id = ?
            """,
            (sale_item_id,)
        )

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                "Позиция продажи не найдена."
            )

        purchase_price = row[0] or 0
        purchase_shipping = row[1] or 0

        profit = (
            sale_price
            - buyer_shipping
            - packaging
            - commission
            - purchase_price
            - purchase_shipping
        )

        cursor.execute(
            """
            UPDATE sale_items
            SET
                sale_price = ?,
                buyer_shipping = ?,
                packaging = ?,
                commission = ?,
                profit = ?
            WHERE id = ?
            """,
            (
                sale_price,
                buyer_shipping,
                packaging,
                commission,
                profit,
                sale_item_id
            )
        )
        cursor.execute(
            """
            SELECT sale_id
            FROM sale_items
            WHERE id = ?
            """,
            (sale_item_id,)
        )

        sale_row = cursor.fetchone()

        if sale_row is not None:
            sale_id = sale_row[0]

            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(sale_price), 0)
                FROM sale_items
                WHERE sale_id = ?
                  AND active = 1
                """,
                (sale_id,)
            )

            total_sale = cursor.fetchone()[0]

            cursor.execute(
                """
                UPDATE sales
                SET total_buyer_paid = ?
                WHERE id = ?
                """,
                (
                    total_sale,
                    sale_id
                )
            )
        connection.commit()

    finally:
        connection.close()
def remove_sale_item(
    sale_item_id
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Находим продажу и экземпляр
        cursor.execute(
            """
            SELECT
                sale_id,
                instance_id
            FROM sale_items
            WHERE id = ?
              AND active = 1
            """,
            (sale_item_id,)
        )

        row = cursor.fetchone()

        if row is None:
            raise ValueError(
                "Активная позиция продажи не найдена."
            )

        sale_id = row[0]
        instance_id = row[1]

        # Удаляем позицию из активной продажи
        cursor.execute(
            """
            DELETE FROM sale_items
            WHERE id = ?
            """,
            (sale_item_id,)
        )

        # Возвращаем экземпляр на склад
        cursor.execute(
            """
            UPDATE instances
            SET status = 'in_stock'
            WHERE id = ?
            """,
            (instance_id,)
        )

        # Пересчитываем общую сумму продажи
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(sale_price), 0)
            FROM sale_items
            WHERE sale_id = ?
              AND active = 1
            """,
            (sale_id,)
        )

        total_sale = cursor.fetchone()[0]

        cursor.execute(
            """
            UPDATE sales
            SET total_buyer_paid = ?
            WHERE id = ?
            """,
            (
                total_sale,
                sale_id
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def get_sale_items(sale_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                sale_items.id,
                sale_items.instance_id,
                instances.product_id,
                instances.internal_number,
                products.manufacturer,
                products.part_number,
                products.name,
                products.barcode,
                instances.purchase_price,
                instances.purchase_shipping,
                sale_items.sale_price,
                sale_items.buyer_shipping,
                sale_items.packaging,
                sale_items.commission,
                sale_items.profit,
                sale_items.active
            FROM sale_items
            JOIN instances
                ON instances.id = sale_items.instance_id
            JOIN products
                ON products.id = instances.product_id
            WHERE sale_items.sale_id = ?
            ORDER BY sale_items.id
            """,
            (sale_id,)
        )

        return cursor.fetchall()

    finally:
        connection.close()
def get_sale(sale_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                id,
                sale_number,
                sale_date,
                total_buyer_paid,
                comment,
                created_at
            FROM sales
            WHERE id = ?
            """,
            (sale_id,)
        )

        return cursor.fetchone()

    finally:
        connection.close()
def update_sale_item_financials(
    sale_item_id,
    sale_price,
    buyer_shipping,
    packaging,
    commission,
    profit
):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE sale_items
            SET
                sale_price = ?,
                buyer_shipping = ?,
                packaging = ?,
                commission = ?,
                profit = ?
            WHERE id = ?
              AND active = 1
            """,
            (
                sale_price,
                buyer_shipping,
                packaging,
                commission,
                profit,
                sale_item_id
            )
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "Активная позиция продажи не найдена."
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def get_sale_id_by_instance(instance_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT sale_id
            FROM sale_items
            WHERE instance_id = ?
              AND active = 1
            LIMIT 1
            """,
            (instance_id,)
        )

        result = cursor.fetchone()

        if result is None:
            return None

        return result[0]

    finally:
        connection.close()
def get_returns():
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                events.event_date,
                instances.internal_number,
                products.manufacturer,
                products.part_number,
                products.name,
                events.comment
            FROM events
            JOIN instances
                ON instances.id = events.instance_id
            JOIN products
                ON products.id = instances.product_id
            WHERE events.event_type = 'return'
            ORDER BY events.id DESC
            """
        )

        return cursor.fetchall()

    finally:
        connection.close()