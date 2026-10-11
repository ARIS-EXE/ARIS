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
                write_offs.comment
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