from database.database import get_connection


def get_next_purchase_number():
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT MAX(purchase_number)
            FROM purchases
            """
        )

        result = cursor.fetchone()[0]

        return (result or 0) + 1

    finally:
        connection.close()
def finalize_purchase(
    purchase_date,
    total_purchase_price,
    total_shipping,
    items
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        purchase_number = get_next_purchase_number()

        cursor.execute(
            """
            INSERT INTO purchases (
                purchase_number,
                purchase_date,
                total_purchase_price,
                total_shipping,
                created_at
            )
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                purchase_number,
                purchase_date,
                total_purchase_price,
                total_shipping
            )
        )

        purchase_id = cursor.lastrowid

        for item in items:
            cursor.execute(
                """
                INSERT INTO purchase_items (
                    purchase_id,
                    instance_id,
                    allocated_purchase_price,
                    allocated_shipping
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    purchase_id,
                    item["instance_id"],
                    item["purchase_price"],
                    item["purchase_shipping"]
                )
            )

            cursor.execute(
                """
                UPDATE instances
                SET
                    purchase_price = ?,
                    purchase_shipping = ?,
                    purchase_date = ?
                WHERE id = ?
                """,
                (
                    item["purchase_price"],
                    item["purchase_shipping"],
                    purchase_date,
                    item["instance_id"]
                )
            )

        connection.commit()

        return purchase_id, purchase_number

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def get_purchases():
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                id,
                purchase_number,
                purchase_date,
                total_purchase_price,
                total_shipping
            FROM purchases
            ORDER BY purchase_number DESC
            """
        )

        return cursor.fetchall()

    finally:
        connection.close()
def get_purchase_items(purchase_id):
    connection = get_connection()
    try:
        cursor = connection.execute("""
            SELECT
                purchase_items.id,
                purchase_items.instance_id,
                instances.internal_number,
                instances.product_id,
                products.manufacturer,
                products.part_number,
                products.name,
                purchase_items.allocated_purchase_price,
                purchase_items.allocated_shipping,
                instances.status,
                instances.listed_date,
                write_offs.comment,
                (
                    SELECT sale_items.profit
                    FROM sale_items
                    WHERE sale_items.instance_id = instances.id
                      AND sale_items.active = 1
                    ORDER BY sale_items.id DESC
                    LIMIT 1
                ) AS sale_profit
            FROM purchase_items
            JOIN instances
                ON instances.id = purchase_items.instance_id
            JOIN products
                ON products.id = instances.product_id
            LEFT JOIN write_offs
                ON write_offs.instance_id = instances.id
            WHERE purchase_items.purchase_id = ?
            ORDER BY purchase_items.id
        """, (purchase_id,))

        return cursor.fetchall()
    finally:
        connection.close()
def get_unlinked_instances():
    connection = get_connection()

    try:
        cursor = connection.execute("""
            SELECT
                instances.id,
                instances.internal_number,
                products.manufacturer,
                products.part_number,
                products.name
            FROM instances
            JOIN products
                ON products.id = instances.product_id
            WHERE instances.deleted = 0
                AND NOT EXISTS (
                    SELECT 1
                    FROM purchase_items
                    WHERE purchase_items.instance_id = instances.id
                )
            ORDER BY instances.internal_number
        """)

        return cursor.fetchall()

    finally:
        connection.close()
def distribute_amount(
    total_amount,
    count
):
    if count <= 0:
        raise ValueError(
            "Количество экземпляров должно быть больше нуля."
        )

    base = total_amount // count
    remainder = total_amount % count

    amounts = []

    for index in range(count):
        amount = base

        if index == 0:
            amount += remainder

        amounts.append(amount)

    return amounts
def create_purchase(
    product_id,
    count,
    total_purchase_price,
    total_shipping,
    purchase_date,
    condition="new"
):
    if count <= 0:
        raise ValueError(
            "Количество экземпляров должно быть больше нуля."
        )

    purchase_prices = distribute_amount(
        total_purchase_price,
        count
    )

    purchase_shippings = distribute_amount(
        total_shipping,
        count
    )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        purchase_number = get_next_purchase_number()

        cursor.execute(
            """
            INSERT INTO purchases (
                purchase_number,
                purchase_date,
                total_purchase_price,
                total_shipping,
                created_at
            )
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                purchase_number,
                purchase_date,
                total_purchase_price,
                total_shipping
            )
        )
        purchase_id = cursor.lastrowid

        for index in range(count):

            cursor.execute(
                """
                SELECT MAX(internal_number)
                FROM instances
                """
            )

            result = cursor.fetchone()[0]

            internal_number = (
                1
                if result is None
                else result + 1
            )

            cursor.execute(
                """
                INSERT INTO instances (
                    internal_number,
                    product_id,
                    condition,
                    purchase_price,
                    purchase_shipping,
                    purchase_date,
                    status,
                    notes,
                    deleted,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    internal_number,
                    product_id,
                    condition,
                    purchase_prices[index],
                    purchase_shippings[index],
                    purchase_date,
                    "in_stock",
                    "",
                    0
                )
            )

            instance_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO purchase_items (
                    purchase_id,
                    instance_id,
                    allocated_purchase_price,
                    allocated_shipping
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    purchase_id,
                    instance_id,
                    purchase_prices[index],
                    purchase_shippings[index]
                )
            )
            cursor.execute(
                """
                INSERT INTO events (
                    event_date,
                    event_type,
                    instance_id,
                    product_id,
                    purchase_id,
                    amount
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    purchase_date,
                    "purchase",
                    instance_id,
                    product_id,
                    purchase_id,
                    purchase_prices[index]
                    + purchase_shippings[index]
                )
            )
        connection.commit()

        return purchase_id, purchase_number

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def create_purchase_multi(
    items,
    total_purchase_price,
    total_shipping,
    purchase_date,
    condition="new",
    existing_instance_ids=None
):
    existing_instance_ids = existing_instance_ids or []

    if not items and not existing_instance_ids:
        raise ValueError(
            "Добавьте хотя бы один товар или экземпляр."
        )

    total_count = len(existing_instance_ids)

    for item in items:
        product_id = item.get("product_id")
        count = item.get("count")

        if product_id is None:
            raise ValueError("Не указан товар.")

        if count is None or count <= 0:
            raise ValueError(
                "Количество экземпляров должно быть больше нуля."
            )

        total_count += count

    if len(set(existing_instance_ids)) != len(existing_instance_ids):
        raise ValueError(
            "Один экземпляр нельзя добавить в закупку повторно."
        )

    if total_count <= 0:
        raise ValueError(
            "Количество экземпляров должно быть больше нуля."
        )

    purchase_prices = distribute_amount(
        total_purchase_price,
        total_count
    )

    purchase_shippings = distribute_amount(
        total_shipping,
        total_count
    )

    purchase_shippings = distribute_amount(
        total_shipping,
        total_count
    )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        purchase_number = get_next_purchase_number()

        cursor.execute(
            """
            INSERT INTO purchases (
                purchase_number,
                purchase_date,
                total_purchase_price,
                total_shipping,
                created_at
            )
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (
                purchase_number,
                purchase_date,
                total_purchase_price,
                total_shipping
            )
        )

        purchase_id = cursor.lastrowid

        price_index = 0

        for item in items:

            product_id = item["product_id"]
            count = item["count"]

            for index in range(count):

                cursor.execute(
                    """
                    SELECT MAX(internal_number)
                    FROM instances
                    """
                )

                result = cursor.fetchone()[0]

                internal_number = (
                    1
                    if result is None
                    else result + 1
                )

                purchase_price = purchase_prices[
                    price_index
                ]

                purchase_shipping = purchase_shippings[
                    price_index
                ]

                cursor.execute(
                    """
                    INSERT INTO instances (
                        internal_number,
                        product_id,
                        condition,
                        purchase_price,
                        purchase_shipping,
                        purchase_date,
                        status,
                        notes,
                        deleted,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        internal_number,
                        product_id,
                        condition,
                        purchase_price,
                        purchase_shipping,
                        purchase_date,
                        "in_stock",
                        "",
                        0
                    )
                )

                instance_id = cursor.lastrowid

                cursor.execute(
                    """
                    INSERT INTO purchase_items (
                        purchase_id,
                        instance_id,
                        allocated_purchase_price,
                        allocated_shipping
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        purchase_id,
                        instance_id,
                        purchase_price,
                        purchase_shipping
                    )
                )
                cursor.execute(
                    """
                    INSERT INTO events (
                        event_date,
                        event_type,
                        instance_id,
                        product_id,
                        purchase_id,
                        amount
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        purchase_date,
                        "purchase",
                        instance_id,
                        product_id,
                        purchase_id,
                        purchase_price
                        + purchase_shipping
                    )
                )
                price_index += 1

        for instance_id in existing_instance_ids:
            cursor.execute(
                """
                SELECT product_id
                FROM instances
                WHERE id = ?
                  AND deleted = 0
                  AND NOT EXISTS (
                      SELECT 1
                      FROM purchase_items
                      WHERE purchase_items.instance_id = instances.id
                  )
                """,
                (instance_id,)
            )

            result = cursor.fetchone()

            if result is None:
                raise ValueError(
                    f"Экземпляр ID {instance_id} уже включён "
                    "в закупку или недоступен."
                )

            product_id = result[0]
            purchase_price = purchase_prices[price_index]
            purchase_shipping = purchase_shippings[price_index]

            cursor.execute(
                """
                UPDATE instances
                SET purchase_price = ?,
                    purchase_shipping = ?,
                    purchase_date = ?
                WHERE id = ?
                """,
                (
                    purchase_price,
                    purchase_shipping,
                    purchase_date,
                    instance_id
                )
            )

            cursor.execute(
                """
                INSERT INTO purchase_items (
                    purchase_id,
                    instance_id,
                    allocated_purchase_price,
                    allocated_shipping
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    purchase_id,
                    instance_id,
                    purchase_price,
                    purchase_shipping
                )
            )

            cursor.execute(
                """
                INSERT INTO events (
                    event_date,
                    event_type,
                    instance_id,
                    product_id,
                    purchase_id,
                    amount
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    purchase_date,
                    "purchase",
                    instance_id,
                    product_id,
                    purchase_id,
                    purchase_price + purchase_shipping
                )
            )

            price_index += 1

        connection.commit()

        return purchase_id, purchase_number

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def update_purchase(
    purchase_id,
    total_purchase_price,
    total_shipping,
    purchase_date,
    items,
    existing_instance_ids=None,
):
    existing_instance_ids = existing_instance_ids or []

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM purchases WHERE id = ?",
            (purchase_id,)
        )
        if cursor.fetchone() is None:
            raise ValueError("Закупка не найдена.")

        # Текущий состав закупки
        cursor.execute(
            """
            SELECT instance_id
            FROM purchase_items
            WHERE purchase_id = ?
            """,
            (purchase_id,)
        )
        old_ids = {row[0] for row in cursor.fetchall()}

        # Новый состав: экземпляры, оставленные в таблице,
        # плюс новые товары и существующие экземпляры.
        kept_ids = set(existing_instance_ids)

        if len(kept_ids) != len(existing_instance_ids):
            raise ValueError("Один экземпляр добавлен несколько раз.")

        new_items = []
        for item in items:
            product_id = item.get("product_id")
            count = item.get("count")

            if product_id is None or not isinstance(count, int) or count <= 0:
                raise ValueError("Проверьте товар и количество.")

            new_items.append({
                "product_id": product_id,
                "count": count,
            })

        # Проверяем экземпляры, которые исключаются из закупки.
        removed_ids = old_ids - kept_ids

        for instance_id in removed_ids:
            cursor.execute(
                """
                SELECT status
                FROM instances
                WHERE id = ?
                """,
                (instance_id,)
            )
            result = cursor.fetchone()

            if result is None:
                raise ValueError(
                    f"Экземпляр ID {instance_id} не найден."
                )

            if result[0] == "sold":
                raise ValueError(
                    "Нельзя исключить из закупки проданный экземпляр."
                )

            cursor.execute(
                """
                SELECT 1
                FROM sale_items
                WHERE instance_id = ?
                  AND active = 1
                LIMIT 1
                """,
                (instance_id,)
            )
            if cursor.fetchone():
                raise ValueError(
                    "Нельзя исключить экземпляр с активной продажей."
                )

        # Проверяем новые существующие экземпляры:
        # они должны быть свободны и не удалены.
        for instance_id in kept_ids - old_ids:
            cursor.execute(
                """
                SELECT id
                FROM instances
                WHERE id = ?
                  AND deleted = 0
                  AND NOT EXISTS (
                      SELECT 1
                      FROM purchase_items
                      WHERE purchase_items.instance_id = instances.id
                  )
                """,
                (instance_id,)
            )
            if cursor.fetchone() is None:
                raise ValueError(
                    f"Экземпляр ID {instance_id} уже связан с закупкой "
                    "или недоступен."
                )

        # Убираем исключённые экземпляры из закупки и инвентаря,
        # сохраняя запись экземпляра в базе.
        for instance_id in removed_ids:
            cursor.execute(
                """
                DELETE FROM purchase_items
                WHERE purchase_id = ?
                  AND instance_id = ?
                """,
                (purchase_id, instance_id)
            )
            cursor.execute(
                """
                UPDATE instances
                SET deleted = 1
                WHERE id = ?
                """,
                (instance_id,)
            )

        # Создаём новые экземпляры для строк с товаром и количеством.
        for item in new_items:
            for _ in range(item["count"]):
                cursor.execute(
                    "SELECT COALESCE(MAX(internal_number), 0) + 1 FROM instances"
                )
                internal_number = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO instances (
                        internal_number,
                        product_id,
                        condition,
                        purchase_price,
                        purchase_shipping,
                        purchase_date,
                        status,
                        notes,
                        deleted,
                        created_at
                    )
                    VALUES (?, ?, 'new', 0, 0, ?, 'in_stock', '', 0,
                            datetime('now'))
                    """,
                    (internal_number, item["product_id"], purchase_date)
                )
                kept_ids.add(cursor.lastrowid)

        final_ids = list(kept_ids)

        if not final_ids:
            raise ValueError("В закупке должен остаться хотя бы один экземпляр.")

        purchase_prices = distribute_amount(
            total_purchase_price, len(final_ids)
        )
        purchase_shippings = distribute_amount(
            total_shipping, len(final_ids)
        )

        cursor.execute(
            """
            UPDATE purchases
            SET purchase_date = ?,
                total_purchase_price = ?,
                total_shipping = ?
            WHERE id = ?
            """,
            (
                purchase_date,
                total_purchase_price,
                total_shipping,
                purchase_id
            )
        )

        for index, instance_id in enumerate(final_ids):
            purchase_price = purchase_prices[index]
            purchase_shipping = purchase_shippings[index]

            cursor.execute(
                """
                SELECT product_id
                FROM instances
                WHERE id = ?
                """,
                (instance_id,)
            )
            product_id = cursor.fetchone()[0]

            cursor.execute(
                """
                UPDATE instances
                SET purchase_price = ?,
                    purchase_shipping = ?,
                    purchase_date = ?
                WHERE id = ?
                """,
                (
                    purchase_price,
                    purchase_shipping,
                    purchase_date,
                    instance_id
                )
            )

            cursor.execute(
                """
                UPDATE purchase_items
                SET allocated_purchase_price = ?,
                    allocated_shipping = ?
                WHERE purchase_id = ?
                  AND instance_id = ?
                """,
                (
                    purchase_price,
                    purchase_shipping,
                    purchase_id,
                    instance_id
                )
            )

            cursor.execute(
                """
                SELECT id
                FROM purchase_items
                WHERE purchase_id = ?
                  AND instance_id = ?
                """,
                (purchase_id, instance_id)
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    INSERT INTO purchase_items (
                        purchase_id,
                        instance_id,
                        allocated_purchase_price,
                        allocated_shipping
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        purchase_id,
                        instance_id,
                        purchase_price,
                        purchase_shipping
                    )
                )

            # Сохраняем событие закупки для новых связей.
            cursor.execute(
                """
                SELECT 1
                FROM events
                WHERE purchase_id = ?
                  AND instance_id = ?
                  AND event_type = 'purchase'
                LIMIT 1
                """,
                (purchase_id, instance_id)
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    INSERT INTO events (
                        event_date,
                        event_type,
                        instance_id,
                        product_id,
                        purchase_id,
                        amount
                    )
                    VALUES (?, 'purchase', ?, ?, ?, ?)
                    """,
                    (
                        purchase_date,
                        instance_id,
                        product_id,
                        purchase_id,
                        purchase_price + purchase_shipping
                    )
                )
            else:
                cursor.execute(
                    """
                    UPDATE events
                    SET event_date = ?,
                        amount = ?
                    WHERE purchase_id = ?
                      AND instance_id = ?
                      AND event_type = 'purchase'
                    """,
                    (
                        purchase_date,
                        purchase_price + purchase_shipping,
                        purchase_id,
                        instance_id
                    )
                )

            # Пересчитываем прибыль активных продаж экземпляра.
            cursor.execute(
                """
                SELECT id, sale_price, buyer_shipping, packaging, commission
                FROM sale_items
                WHERE instance_id = ?
                  AND active = 1
                """,
                (instance_id,)
            )

            for sale in cursor.fetchall():
                sale_item_id, sale_price, buyer_shipping, packaging, commission = sale

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
                    SET profit = ?
                    WHERE id = ?
                      AND active = 1
                    """,
                    (profit, sale_item_id)
                )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def delete_purchase_instance(instance_id):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT status
            FROM instances
            WHERE id = ?
        """, (instance_id,))

        result = cursor.fetchone()

        if result is None:
            raise ValueError("Экземпляр не найден.")

        if result[0] == "sold":
            raise ValueError(
                "Проданный экземпляр нельзя удалить."
            )

        cursor.execute("""
            DELETE FROM purchase_items
            WHERE instance_id = ?
        """, (instance_id,))

        cursor.execute("""
            DELETE FROM instances
            WHERE id = ?
        """, (instance_id,))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def get_purchase_id_by_instance(instance_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT purchase_id
            FROM purchase_items
            WHERE instance_id = ?
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