from database.database import get_connection


def get_next_internal_number():
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT MAX(internal_number)
            FROM instances
            """
        )

        result = cursor.fetchone()[0]

        if result is None:
            return 1

        return result + 1

    finally:
        connection.close()

def create_instance(
    product_id,
    condition="new",
    purchase_price=0,
    purchase_shipping=0,
    purchase_date=None,
    notes=""
):
    from datetime import date

    if purchase_date is None:
        purchase_date = date.today().isoformat()

    internal_number = get_next_internal_number()

    connection = get_connection()

    try:
        cursor = connection.execute(
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
                notes,
                0
            )
        )

        connection.commit()

        return cursor.lastrowid

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_instance_by_number(internal_number):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                id,
                internal_number,
                product_id,
                condition,
                purchase_price,
                purchase_shipping,
                purchase_date,
                status,
                notes,
                deleted,
                created_at,
                listed_date
            FROM instances
            WHERE internal_number = ?
        """,
            (internal_number,)
        )

        return cursor.fetchone()

    finally:
        connection.close()
def get_instance(instance_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                id,
                internal_number,
                product_id,
                condition,
                purchase_price,
                purchase_shipping,
                purchase_date,
                status,
                notes,
                deleted,
                created_at,
                listed_date
            FROM instances
            WHERE id = ?
            """,
            (instance_id,)
        )

        return cursor.fetchone()

    finally:
        connection.close()

def get_instances_by_product(product_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                instances.id,
                instances.internal_number,
                instances.product_id,
                instances.condition,
                instances.purchase_price,
                instances.purchase_shipping,
                instances.purchase_date,
                instances.status,
                instances.notes,
                instances.deleted,
                instances.created_at,
                instances.listed_date,
                write_offs.comment
            FROM instances
            LEFT JOIN write_offs
                ON write_offs.instance_id = instances.id
            WHERE instances.product_id = ?
              AND instances.deleted = 0
            ORDER BY instances.internal_number
            """,
            (product_id,)
        )

        return cursor.fetchall()

    finally:
        connection.close()

def get_in_stock_count(product_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT COUNT(*)
            FROM instances
            WHERE product_id = ?
              AND status = 'in_stock'
              AND deleted = 0
            """,
            (product_id,)
        )

        return cursor.fetchone()[0]

    finally:
        connection.close()

def update_instance_status(instance_id, status):
    allowed_statuses = {
        "in_stock",
        "sold",
        "written_off"
    }

    if status not in allowed_statuses:
        raise ValueError(
            f"Недопустимый статус экземпляра: {status}"
        )

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT status
            FROM instances
            WHERE id = ?
            """,
            (instance_id,)
        )

        result = cursor.fetchone()

        if result is None:
            raise ValueError("Экземпляр не найден.")

        current_status = result[0]

        if current_status == "written_off" and status == "written_off":
            raise ValueError("Этот экземпляр уже списан.")

        connection.execute(
            """
            UPDATE instances
            SET status = ?
            WHERE id = ?
            """,
            (
                status,
                instance_id
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def delete_instance(instance_id):
    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE instances
            SET deleted = 1
            WHERE id = ?
            """,
            (instance_id,)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def restore_instance(instance_id):
    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE instances
            SET deleted = 0
            WHERE id = ?
            """,
            (instance_id,)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def search_instances(search_text):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT
                instances.id,
                instances.product_id,
                instances.internal_number,
                products.manufacturer,
                products.part_number,
                products.name,
                products.barcode,
                instances.condition,
                instances.purchase_price,
                instances.purchase_shipping,
                products.default_buyer_shipping,
                products.default_packaging,
                products.default_delivery_option_id,
                products.default_commission_type,
                products.default_commission_value
            FROM instances
            JOIN products
                ON products.id = instances.product_id
            WHERE instances.deleted = 0
              AND instances.status = 'in_stock'
              AND (
                  CAST(instances.internal_number AS TEXT) LIKE ?
                  OR products.barcode LIKE ?
                  OR products.manufacturer LIKE ?
                  OR products.part_number LIKE ?
                  OR products.name LIKE ?
              )
            ORDER BY instances.internal_number
            """,
            (
                f"%{search_text}%",
                f"%{search_text}%",
                f"%{search_text}%",
                f"%{search_text}%",
                f"%{search_text}%"
            )
        )

        results = cursor.fetchall()
        return results

    finally:
        connection.close()
def create_instances_batch(
    product_id,
    count,
    purchase_prices,
    purchase_shippings,
    purchase_date,
    condition="new"
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        instance_ids = []

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

            instance_ids.append(
                cursor.lastrowid
            )

        connection.commit()

        return instance_ids

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
def write_off_instance(instance_id, comment):
    from datetime import date

    comment = comment.strip()

    if not comment:
        raise ValueError("Причина списания обязательна.")

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            SELECT status
            FROM instances
            WHERE id = ?
            """,
            (instance_id,)
        )

        result = cursor.fetchone()

        if result is None:
            raise ValueError("Экземпляр не найден.")

        if result[0] == "written_off":
            raise ValueError("Этот экземпляр уже списан.")

        if result[0] == "sold":
            raise ValueError("Проданный экземпляр нельзя списать.")

        cursor = connection.execute(
            """
            INSERT INTO write_offs (
                instance_id,
                write_off_date,
                comment
            )
            VALUES (?, ?, ?)
            """,
            (
                instance_id,
                date.today().isoformat(),
                comment
            )
        )

        write_off_id = cursor.lastrowid

        connection.execute(
            """
            UPDATE instances
            SET status = 'written_off'
            WHERE id = ?
            """,
            (instance_id,)
        )

        connection.execute(
            """
            INSERT INTO events (
                event_date,
                event_type,
                instance_id,
                write_off_id,
                comment
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                date.today().isoformat(),
                "write_off",
                instance_id,
                write_off_id,
                comment
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()