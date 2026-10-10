from datetime import date

from database.database import get_connection


def get_month_range(year, month):
    if month == 12:
        next_year = year + 1
        next_month = 1
    else:
        next_year = year
        next_month = month + 1

    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{next_year:04d}-{next_month:02d}-01"

    return start_date, end_date


def get_month_data(year, month):
    start_date, end_date = get_month_range(
        year,
        month
    )

    connection = get_connection()

    try:
        # Прибыль.
        #
        # Если продажа была возвращена,
        # sale_items.active становится 0.
        # Поэтому прибыль этой продажи
        # больше не учитывается в месяце продажи.
        cursor = connection.execute(
            """
            SELECT COALESCE(
                SUM(sale_items.profit),
                0
            )
            FROM sale_items
            JOIN sales
                ON sales.id = sale_items.sale_id
            WHERE sales.sale_date >= ?
              AND sales.sale_date < ?
              AND sale_items.active = 1
            """,
            (
                start_date,
                end_date
            )
        )

        profit = cursor.fetchone()[0]

        # Расходы = стоимость закупленных товаров
        # + доставка закупок.
        cursor = connection.execute(
            """
            SELECT
                COALESCE(SUM(total_purchase_price), 0),
                COALESCE(SUM(total_shipping), 0)
            FROM purchases
            WHERE purchase_date >= ?
              AND purchase_date < ?
            """,
            (
                start_date,
                end_date
            )
        )

        purchase_price, purchase_shipping = (
            cursor.fetchone()
        )

        expenses = (
            purchase_price
            + purchase_shipping
        )

        # Количество купленных экземпляров.
        cursor = connection.execute(
            """
            SELECT COUNT(*)
            FROM purchase_items
            JOIN purchases
                ON purchases.id = purchase_items.purchase_id
            WHERE purchases.purchase_date >= ?
              AND purchases.purchase_date < ?
            """,
            (
                start_date,
                end_date
            )
        )

        purchased = cursor.fetchone()[0]

        # Количество проданных экземпляров.
        #
        # Возвращённые товары имеют active = 0,
        # поэтому в количестве проданных
        # они больше не учитываются.
        cursor = connection.execute(
            """
            SELECT COUNT(*)
            FROM sale_items
            JOIN sales
                ON sales.id = sale_items.sale_id
            WHERE sales.sale_date >= ?
              AND sales.sale_date < ?
              AND sale_items.active = 1
            """,
            (
                start_date,
                end_date
            )
        )

        sold = cursor.fetchone()[0]

        # Количество возвратов.
        cursor = connection.execute(
            """
            SELECT COUNT(*)
            FROM returns
            WHERE return_date >= ?
              AND return_date < ?
            """,
            (
                start_date,
                end_date
            )
        )

        returned = cursor.fetchone()[0]

        # Количество экземпляров, выставленных на продажу
        # в течение этого месяца.
        cursor = connection.execute(
            """
            SELECT COUNT(*)
            FROM instances
            WHERE listed_date >= ?
              AND listed_date < ?
              AND deleted = 0
            """,
            (
                start_date,
                end_date
            )
        )

        in_stock = cursor.fetchone()[0]

        return {
            "profit": profit,
            "expenses": expenses,
            "in_stock": in_stock,
            "sold": sold,
            "purchased": purchased,
            "returned": returned,
        }

    finally:
        connection.close()


def get_dashboard_months():
    today = date.today()

    months = []

    year = today.year
    month = today.month

    for _ in range(4):
        data = get_month_data(
            year,
            month
        )

        months.append({
            "year": year,
            "month": month,
            "profit": data["profit"],
            "expenses": data["expenses"],
            "in_stock": data["in_stock"],
            "sold": data["sold"],
            "purchased": data["purchased"],
            "returned": data["returned"],
        })

        month -= 1

        if month == 0:
            month = 12
            year -= 1

    months.reverse()

    return months
def get_last_12_months():
    today = date.today()

    months = []

    year = today.year
    month = today.month

    for _ in range(12):
        data = get_month_data(
            year,
            month
        )

        months.append({
            "year": year,
            "month": month,
            "expenses": data["expenses"],
            "profit": data["profit"],
        })

        month -= 1

        if month == 0:
            month = 12
            year -= 1

    months.reverse()

    return months