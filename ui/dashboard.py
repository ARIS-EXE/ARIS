from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)

from PySide6.QtCharts import (
    QChart,
    QChartView,
    QLineSeries,
    QCategoryAxis,
)

from models.dashboard import (
    get_dashboard_months,
    get_last_12_months,
)

class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_month_block = None
        self.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus
        )
        main_layout = QVBoxLayout(self)
        data = get_dashboard_months()

        # График — последние 12 месяцев
        chart_frame = QFrame()
        chart_frame.setFrameShape(QFrame.StyledPanel)

        chart_layout = QVBoxLayout(chart_frame)

        chart_title = QLabel(
            "Расходы и прибыль — последние 12 месяцев"
        )
        chart_title.setStyleSheet(
            "font-size: 16px; font-weight: bold;"
        )

        chart_layout.addWidget(chart_title)

        months_data = get_last_12_months()

        expenses_series = QLineSeries()
        expenses_series.setName("Расходы")

        profit_series = QLineSeries()
        profit_series.setName("Прибыль")

        for index, month_data in enumerate(months_data):
            expenses_series.append(
                index,
                month_data["expenses"]
            )

            profit_series.append(
                index,
                month_data["profit"]
            )

        chart = QChart()
        chart.addSeries(expenses_series)
        chart.addSeries(profit_series)

        chart.setTitle(
            "Расходы и прибыль"
        )

        chart.legend().setVisible(True)

        axis_x = QCategoryAxis()

        for index, month_data in enumerate(months_data):
            label = (
                f"{month_data['month']:02d}."
                f"{str(month_data['year'])[-2:]}"
            )

            axis_x.append(
                label,
                index
            )

        chart.addAxis(
            axis_x,
            Qt.AlignmentFlag.AlignBottom
        )

        expenses_series.attachAxis(axis_x)
        profit_series.attachAxis(axis_x)

        chart_view = QChartView(chart)
        chart_view.setMinimumHeight(300)

        chart_layout.addWidget(chart_view)

        main_layout.addWidget(chart_frame)

        # Блоки последних 4 месяцев
        months_layout = QHBoxLayout()

        for month_data in data:
            month_name = self.get_month_name(
                month_data["month"]
            )

            month_title = (
                f"{month_name} "
                f"{month_data['year']}"
            )

            month_block = self.create_month_block(
                month_title,
                month_data
            )

            months_layout.addWidget(
                month_block
            )

        main_layout.addLayout(months_layout)

        main_layout.addStretch()

    def get_month_name(self, month):
        months = [
            "Январь",
            "Февраль",
            "Март",
            "Апрель",
            "Май",
            "Июнь",
            "Июль",
            "Август",
            "Сентябрь",
            "Октябрь",
            "Ноябрь",
            "Декабрь",
        ]

        return months[month - 1]


    def create_month_block(self, title, data):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setProperty("copy_text", "\n".join([
            title,
            f"Прибыль: {data['profit']} ¥",
            f"Расходы: {data['expenses']} ¥",
            f"В продаже: {data['in_stock']} шт.",
            f"Продано: {data['sold']} шт.",
            f"Куплено: {data['purchased']} шт.",
            f"Возвраты: {data['returned']} шт.",
        ]))
        frame.mousePressEvent = (
            lambda event, block=frame:
            self.select_month_block(block)
        )

        layout = QVBoxLayout(frame)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        values = [
            ("Прибыль", f"{data['profit']} ¥"),
            ("Расходы", f"{data['expenses']} ¥"),
            ("В продаже", f"{data['in_stock']} шт."),
            ("Продано", f"{data['sold']} шт."),
            ("Куплено", f"{data['purchased']} шт."),
            ("Возвраты", f"{data['returned']} шт."),
        ]

        for name, value in values:
            row = QHBoxLayout()

            name_label = QLabel(name)
            value_label = QLabel(value)
            value_label.setStyleSheet(
                "font-weight: bold;"
            )

            row.addWidget(name_label)
            row.addStretch()
            row.addWidget(value_label)
            layout.addLayout(row)

        layout.addStretch()
        return frame

    def select_month_block(self, block):
        if self.selected_month_block is not None:
            self.selected_month_block.setStyleSheet("")

        self.selected_month_block = block

        block.setStyleSheet("""
            QFrame {
                background-color: #F0F6FC;
                border: 1px solid #B8D4F0;
                border-radius: 8px;
            }
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)

        self.setFocus()


    def keyPressEvent(self, event):
        if (
            event.key() == Qt.Key.Key_C
            and event.modifiers()
            & Qt.KeyboardModifier.ControlModifier
        ):
            block = self.selected_month_block

            if block is not None:
                QApplication.clipboard().setText(
                    block.property("copy_text")
                )
                event.accept()
                return

        super().keyPressEvent(event)
    def refresh(self):
        self.selected_month_block = None
        # Полностью удаляем старое содержимое,
        # включая вложенные layouts.
        def clear_layout(layout):
            while layout.count():
                item = layout.takeAt(0)

                widget = item.widget()

                if widget is not None:
                    widget.deleteLater()

                child_layout = item.layout()

                if child_layout is not None:
                    clear_layout(child_layout)

        main_layout = self.layout()

        clear_layout(main_layout)

        # Загружаем свежие данные
        data = get_dashboard_months()

        # График
        chart_frame = QFrame()
        chart_frame.setFrameShape(QFrame.StyledPanel)

        chart_layout = QVBoxLayout(chart_frame)

        chart_title = QLabel(
            "Расходы и прибыль — последние 12 месяцев"
        )
        chart_title.setStyleSheet(
            "font-size: 16px; font-weight: bold;"
        )

        chart_layout.addWidget(chart_title)

        months_data = get_last_12_months()

        expenses_series = QLineSeries()
        expenses_series.setName("Расходы")

        profit_series = QLineSeries()
        profit_series.setName("Прибыль")

        for index, month_data in enumerate(months_data):
            expenses_series.append(
                index,
                month_data["expenses"]
            )

            profit_series.append(
                index,
                month_data["profit"]
            )

        chart = QChart()

        chart.addSeries(expenses_series)
        chart.addSeries(profit_series)

        chart.legend().setVisible(True)

        axis_x = QCategoryAxis()

        for index, month_data in enumerate(months_data):
            label = (
                f"{month_data['month']:02d}."
                f"{str(month_data['year'])[-2:]}"
            )

            axis_x.append(
                label,
                index
            )

        chart.addAxis(
            axis_x,
            Qt.AlignmentFlag.AlignBottom
        )

        expenses_series.attachAxis(axis_x)
        profit_series.attachAxis(axis_x)

        chart_view = QChartView(chart)
        chart_view.setMinimumHeight(300)

        chart_layout.addWidget(chart_view)

        main_layout.addWidget(chart_frame)

        # Блоки последних 4 месяцев
        months_layout = QHBoxLayout()

        for month_data in data:
            month_name = self.get_month_name(
                month_data["month"]
            )

            month_title = (
                f"{month_name} "
                f"{month_data['year']}"
            )

            month_block = self.create_month_block(
                month_title,
                month_data
            )

            months_layout.addWidget(
                month_block
            )

        main_layout.addLayout(months_layout)

        main_layout.addStretch()