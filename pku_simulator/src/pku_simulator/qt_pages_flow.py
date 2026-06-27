"""流程页面。

这些是后台 QWidget 页面：开始页、采购商店和失败页。正常游玩主要显示
`GameSceneView` 的图形覆盖层；这些页面在开发控件或失败页中作为后备 UI。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from pku_simulator.core.catalog import CATALOG, SHOP_LIST
from pku_simulator.qt_scene import BasePage


class StartPage(BasePage):
    """开始页后台控件；图形开始页按钮最终也会调用 `open_start_shop()`。"""

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)
        layout.addStretch(1)

        self.title_label = QLabel("PKU 模拟经营")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(30)
        title_font.setBold(True)
        self.title_label.setFont(title_font)

        self.day_label = QLabel()
        self.day_label.setAlignment(Qt.AlignCenter)
        self.day_label.setStyleSheet("font-size: 24px;")

        self.balance_label = QLabel()
        self.balance_label.setAlignment(Qt.AlignCenter)
        self.balance_label.setStyleSheet("font-size: 18px; color: #334155;")

        hint_label = QLabel("点击开餐进入采购，再开始当天营业")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("font-size: 15px; color: #64748b;")

        self.open_button = QPushButton("开餐")
        self.open_button.setFixedHeight(54)
        self.open_button.setStyleSheet(
            "QPushButton {"
            "background-color: #b91c1c;"
            "color: white;"
            "border-radius: 10px;"
            "font-size: 20px;"
            "font-weight: 600;"
            "padding: 8px 20px;"
            "}"
            "QPushButton:hover { background-color: #991b1b; }"
        )
        self.open_button.clicked.connect(self._go_to_shop)

        layout.addWidget(self.title_label)
        layout.addWidget(self.day_label)
        layout.addWidget(self.balance_label)
        layout.addWidget(hint_label)
        layout.addSpacing(12)
        layout.addWidget(self.open_button, alignment=Qt.AlignHCenter)
        layout.addStretch(2)

    def on_enter(self) -> None:
        """进入开始页时刷新天数和余额。"""
        self.day_label.setText(f"第 {self.state.day} 天")
        self.balance_label.setText(f"账户余额: $ {self.state.balance:.2f}")

    def _go_to_shop(self) -> None:
        self.main_window.open_start_shop()


class ShopPage(BasePage):
    """采购商店后台控件；图形商店覆盖层共用同一套主窗口商店接口。"""

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)

        self._message_text = ""
        self._message_success = True
        self._inventory_cells: dict[str, QTableWidgetItem] = {}
        self._price_cells: dict[str, QTableWidgetItem] = {}
        self._buy_buttons: dict[str, QPushButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("采购商店")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")

        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 15px; color: #334155;")

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("font-size: 14px;")

        self.table = QTableWidget(len(SHOP_LIST), 4)
        self.table.setHorizontalHeaderLabels(["食材", "单价", "库存", "操作"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget {"
            " background: #fffdf7;"
            " gridline-color: #e2e8f0;"
            " font-size: 16px;"
            "}"
            "QHeaderView::section {"
            " background: #f8fafc;"
            " color: #0f172a;"
            " font-size: 17px;"
            " font-weight: 600;"
            " padding: 10px 12px;"
            " border: 0;"
            " border-bottom: 1px solid #cbd5e1;"
            "}"
            "QTableWidget::item {"
            " padding: 10px 12px;"
            "}"
            "QPushButton {"
            " font-size: 15px;"
            " padding: 8px 14px;"
            " border-radius: 8px;"
            "}"
        )
        self.table.setRowHeight(0, 96)
        for row in range(len(SHOP_LIST)):
            self.table.setRowHeight(row, 96)
        self.table.setColumnWidth(0, 240)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 110)
        self.table.horizontalHeader().setStretchLastSection(True)

        for row, key in enumerate(SHOP_LIST):
            ingredient = CATALOG[key]

            name_item = QTableWidgetItem(ingredient.name)
            price_item = QTableWidgetItem("")
            inventory_item = QTableWidgetItem("0")

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, price_item)
            self.table.setItem(row, 2, inventory_item)
            self._price_cells[key] = price_item
            self._inventory_cells[key] = inventory_item

            buy_button = QPushButton("购买")
            buy_button.clicked.connect(lambda _checked=False, item_key=key: self._buy(item_key))
            self.table.setCellWidget(row, 3, buy_button)
            self._buy_buttons[key] = buy_button

        self.confirm_button = QPushButton("完成采购并开始营业")
        self.confirm_button.setFixedHeight(42)
        self.confirm_button.setStyleSheet(
            "QPushButton {"
            "background-color: #dc2626;"
            "color: white;"
            "border-radius: 8px;"
            "font-size: 16px;"
            "font-weight: 600;"
            "}"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        self.confirm_button.clicked.connect(self._confirm)

        root.addWidget(title)
        root.addWidget(self.status_label)
        root.addWidget(self.message_label)
        root.addWidget(self.table)
        root.addWidget(self.confirm_button)

    def on_enter(self) -> None:
        self._refresh()

    def _set_message(self, text: str, success: bool) -> None:
        self._message_text = text
        self._message_success = success

    def _buy(self, key: str) -> None:
        """后台购买按钮入口；实际业务在 `ShopControllerMixin`。"""
        success, message = self.main_window.buy_shop_ingredient(key, quantity=1)
        self._set_message(message, success)
        self._refresh()

    def _confirm(self) -> None:
        """后台完成采购入口；开局采购和补货由主窗口区分。"""
        self.main_window.finish_shop_purchase()

    def _refresh(self) -> None:
        """刷新余额、价格、库存和按钮可用性。"""
        multiplier = self.main_window.shop_price_multiplier()
        surcharge_text = " | 营业中补货价 +20%" if multiplier > 1.0 else ""
        self.status_label.setText(
            f"第 {self.state.day} 天 | 余额: $ {self.state.balance:.2f} | 欠费下限: $ {self.state.debt_limit:.2f}{surcharge_text}"
        )

        if self._message_text:
            color = "#166534" if self._message_success else "#9a3412"
            self.message_label.setStyleSheet(f"font-size: 14px; color: {color};")
            self.message_label.setText(self._message_text)
        else:
            self.message_label.setText("")

        for key in SHOP_LIST:
            price = self.main_window.shop_unit_price(key)
            price_suffix = " (+20%)" if multiplier > 1.0 else ""
            self._price_cells[key].setText(f"$ {price:.2f}{price_suffix}")
            self._inventory_cells[key].setText(str(self.service.get_quantity(key)))
            can_buy = self.state.can_spend(price)
            self._buy_buttons[key].setEnabled(can_buy)


class GameOverPage(BasePage):
    """失败页后台控件；重开按钮调用主窗口 `reset_game()`。"""

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(14)
        root.addStretch(1)

        title = QLabel("经营失败")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 36px; font-weight: 800; color: #7f1d1d;")

        self.reason_label = QLabel()
        self.reason_label.setAlignment(Qt.AlignCenter)
        self.reason_label.setStyleSheet("font-size: 17px;")

        hint = QLabel("规则：当日结算后欠费达到 200，游戏结束。")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("font-size: 14px; color: #64748b;")

        restart_button = QPushButton("重新开始")
        restart_button.setFixedHeight(46)
        restart_button.setStyleSheet(
            "QPushButton {"
            "background-color: #be123c;"
            "color: white;"
            "border-radius: 9px;"
            "font-size: 16px;"
            "font-weight: 700;"
            "padding: 6px 20px;"
            "}"
            "QPushButton:hover { background-color: #9f1239; }"
        )
        restart_button.clicked.connect(self.main_window.reset_game)

        root.addWidget(title)
        root.addWidget(self.reason_label)
        root.addWidget(hint)
        root.addSpacing(14)
        root.addWidget(restart_button, alignment=Qt.AlignHCenter)
        root.addStretch(2)

    def on_enter(self) -> None:
        """进入失败页时展示破产余额。"""
        self.reason_label.setText(
            f"余额已达到 $ {self.state.balance:.2f}（<= $ {self.state.game_over_debt:.2f}）"
        )
