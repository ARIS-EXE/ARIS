
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QMessageBox,
)

from database.database import get_connection


class ProductStatisticsDialog(QDialog):
    def __init__(self, product_id, parent=None):
        super().__init__(parent)

        self.product_id = product_id

        self.setWindowTitle("Статистика товара")
        self.resize(520, 400)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        form_layout.setVerticalSpacing(12)
        form_layout.setHorizontalSpacing(24)

        self.values = {}

        indicators = [
            ("sold_count", "Количество проданных экземпляров"),
            ("purchase_price", "Средняя закупочная цена"),
            ("purchase_shipping", "Средняя закупочная доставка"),
            ("sale_price", "Средняя цена продажи"),
            ("profit", "Средняя прибыль"),
            ("revenue_after_expenses", "Средняя прибыль + себестоимость"),
            ("sale_days", "Среднее время продажи"),
        ]

        for key, title in indicators:
            value_label = QLabel("—")
            value_label.setTextInteractionFlags(
                value_label.textInteractionFlags()
                | value_label.textInteractionFlags().TextSelectableByMouse
            )

            form_layout.addRow(
                f"{title}:",
                value_label
            )

            self.values[key] = value_label

        main_layout.addLayout(form_layout)

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)

        main_layout.addWidget(close_button)

        self.load_statistics()

    def load_statistics(self):
        connection = get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    AVG(i.purchase_price),
                    AVG(i.purchase_shipping),
                    AVG(si.sale_price),
                    AVG(si.profit),
                    AVG(
                        si.sale_price
                        - si.commission
                        - si.packaging
                        - si.buyer_shipping
                    )
                FROM sale_items AS si
                JOIN sales AS s
                    ON s.id = si.sale_id
                JOIN instances AS i
                    ON i.id = si.instance_id
                WHERE i.product_id = ?
                  AND si.active = 1
                """,
                (self.product_id,)
            )

            row = cursor.fetchone()

            cursor.execute(
                """
                SELECT AVG(
                    julianday(s.sale_date)
                    - julianday(
                        (
                            SELECT e.event_date
                            FROM events AS e
                            WHERE e.instance_id = si.instance_id
                              AND e.event_type = 'listed'
                              AND e.id < (
                                  SELECT MIN(se.id)
                                  FROM events AS se
                                  WHERE se.instance_id = si.instance_id
                                    AND se.sale_id = s.id
                                    AND se.event_type = 'sale'
                              )
                            ORDER BY e.id DESC
                            LIMIT 1
                        )
                    )
                )
                FROM sale_items AS si
                JOIN sales AS s
                    ON s.id = si.sale_id
                JOIN instances AS i
                    ON i.id = si.instance_id
                WHERE i.product_id = ?
                  AND si.active = 1
                  AND EXISTS (
                      SELECT 1
                      FROM events AS se
                      WHERE se.instance_id = si.instance_id
                        AND se.sale_id = s.id
                        AND se.event_type = 'sale'
                  )
                  AND (
                      SELECT e.event_date
                      FROM events AS e
                      WHERE e.instance_id = si.instance_id
                        AND e.event_type = 'listed'
                        AND e.id < (
                            SELECT MIN(se.id)
                            FROM events AS se
                            WHERE se.instance_id = si.instance_id
                              AND se.sale_id = s.id
                              AND se.event_type = 'sale'
                        )
                      ORDER BY e.id DESC
                      LIMIT 1
                  ) IS NOT NULL
                """,
                (self.product_id,)
            )

            average_days = cursor.fetchone()[0]

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось загрузить статистику:\n\n{error}"
            )
            self.reject()
            return

        finally:
            connection.close()

        sold_count = row[0] or 0

        self.values["sold_count"].setText(
            str(sold_count)
        )

        if sold_count == 0:
            for key in (
                "purchase_price",
                "purchase_shipping",
                "sale_price",
                "profit",
                "revenue_after_expenses",
                "sale_days",
            ):
                self.values[key].setText("Нет данных")

            return

        money_values = {
            "purchase_price": row[1],
            "purchase_shipping": row[2],
            "sale_price": row[3],
            "profit": row[4],
            "revenue_after_expenses": row[5],
        }

        for key, value in money_values.items():
            if value is None:
                text = "Нет данных"
            else:
                text = f"{value:,.2f} ¥"

            self.values[key].setText(text)

        if average_days is None:
            self.values["sale_days"].setText("Нет данных")
        else:
            self.values["sale_days"].setText(
                f"{average_days:.1f} дн."
            )
