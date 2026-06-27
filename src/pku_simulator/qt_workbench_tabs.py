"""营业区后台表格控件。

这些 QWidget 标签页主要用于开发/调试或无图形模式下操作。真实图形玩法的
拖拽和按钮由 `qt_scene_drag.py`、`qt_workbench_drops.py` 和覆盖层模块处理。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from pku_simulator.core.catalog import CATALOG
from pku_simulator.services.game_service import BBQ_SKEWER_KEYS, GRIDDLE_ORDER_KEYS

if TYPE_CHECKING:
    from pku_simulator.qt_pages_workbench import WorkbenchPage


class GriddleTab(QWidget):
    """烤盘后台控件；手动组合配方并写入出餐仓。"""

    def __init__(self, workbench: WorkbenchPage) -> None:
        super().__init__()
        self.workbench = workbench
        self._recipe_counts: dict[str, int] = {}
        self._consumed_recipe_counts: dict[str, int] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        helper = QLabel("可自由组合食材并设置份数，支持重复食材。")
        helper.setStyleSheet("color: #475569;")

        add_bar = QHBoxLayout()
        self.ingredient_combo = QComboBox()
        for key in GRIDDLE_ORDER_KEYS:
            self.ingredient_combo.addItem(CATALOG[key].name, key)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 8)
        self.quantity_spin.setValue(1)

        add_button = QPushButton("加入配方")
        add_button.clicked.connect(self._add_item)

        clear_button = QPushButton("清空配方")
        clear_button.clicked.connect(self._clear_recipe)

        add_bar.addWidget(QLabel("食材:"))
        add_bar.addWidget(self.ingredient_combo)
        add_bar.addWidget(QLabel("份数:"))
        add_bar.addWidget(self.quantity_spin)
        add_bar.addWidget(add_button)
        add_bar.addWidget(clear_button)
        add_bar.addStretch(1)

        self.recipe_view = QTextEdit()
        self.recipe_view.setReadOnly(True)
        self.recipe_view.setFixedHeight(160)

        action_group = QGroupBox("出锅设置")
        action_form = QFormLayout(action_group)

        self.cook_spin = QSpinBox()
        self.cook_spin.setRange(1, 300)
        self.cook_spin.setValue(20)

        self.edible_check = QCheckBox("可食用")
        self.edible_check.setChecked(True)

        cook_button = QPushButton("出锅并写入出餐仓")
        cook_button.clicked.connect(self._cook)

        action_form.addRow("烹饪时长(秒):", self.cook_spin)
        action_form.addRow("状态:", self.edible_check)
        action_form.addRow(cook_button)

        root.addWidget(helper)
        root.addLayout(add_bar)
        root.addWidget(self.recipe_view)
        root.addWidget(action_group)

        self._refresh_recipe_view()

    def _add_item(self) -> None:
        key = self.ingredient_combo.currentData()
        count = self.quantity_spin.value()
        self._recipe_counts[key] = self._recipe_counts.get(key, 0) + count
        self._refresh_recipe_view()

    def _clear_recipe(self) -> None:
        self._recipe_counts.clear()
        self._consumed_recipe_counts.clear()
        self._refresh_recipe_view()

    def add_dragged_ingredient(self, key: str) -> None:
        """兼容旧图形拖拽入口：把已扣库存的食材加入后台配方。"""
        self._recipe_counts[key] = self._recipe_counts.get(key, 0) + 1
        self._consumed_recipe_counts[key] = self._consumed_recipe_counts.get(key, 0) + 1
        self._refresh_recipe_view()

    def _refresh_recipe_view(self) -> None:
        if not self._recipe_counts:
            self.recipe_view.setPlainText("当前配方为空。")
            return

        lines = ["当前烤盘配方:"]
        total = 0
        for key, count in self._recipe_counts.items():
            total += count
            lines.append(f"- {CATALOG[key].name} x {count}")
        lines.append("")
        lines.append(f"总份数: {total}")
        self.recipe_view.setPlainText("\n".join(lines))

    def _cook(self) -> None:
        """校验库存并把当前配方记录为一份烤盘菜。"""
        if not self._recipe_counts:
            self.workbench.notify_message("当前配方为空。", success=False)
            return

        missing: list[str] = []
        for key, count in self._recipe_counts.items():
            count_to_consume = max(0, count - self._consumed_recipe_counts.get(key, 0))
            available = self.workbench.service.get_quantity(key)
            if available < count_to_consume:
                missing.append(f"{CATALOG[key].name} 库存 {available}/{count_to_consume}")

        if missing:
            self.workbench.notify_message("库存不足：" + "，".join(missing), success=False)
            return

        for key, count in self._recipe_counts.items():
            count_to_consume = max(0, count - self._consumed_recipe_counts.get(key, 0))
            if count_to_consume == 0:
                continue
            success, message = self.workbench.service.consume_ingredient(key, count_to_consume)
            if not success:
                self.workbench.notify_message(message, success=False)
                self.workbench.refresh_station_assets()
                return

        ingredient_keys: list[str] = []
        for key, count in self._recipe_counts.items():
            ingredient_keys.extend([key] * count)

        self.workbench.add_prepared_dishes(
            station="griddle",
            ingredient_keys=ingredient_keys,
            edible=self.edible_check.isChecked(),
            cook_seconds=float(self.cook_spin.value()),
            quantity=1,
        )
        self._recipe_counts.clear()
        self._consumed_recipe_counts.clear()
        self._refresh_recipe_view()
        self.workbench.refresh_station_assets()


class CheungFunTab(QWidget):
    """肠粉后台控件；固定包含面糊，可勾选鸡蛋和鲜虾。"""

    def __init__(self, workbench: WorkbenchPage) -> None:
        super().__init__()
        self.workbench = workbench

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        hint = QLabel("肠粉基础面糊固定包含，额外可选鸡蛋/鲜虾。")
        hint.setStyleSheet("color: #475569;")

        grid = QGridLayout()

        self.egg_check = QCheckBox("加鸡蛋")
        self.shrimp_check = QCheckBox("加鲜虾")
        self.edible_check = QCheckBox("可食用")
        self.edible_check.setChecked(True)

        self.cook_spin = QSpinBox()
        self.cook_spin.setRange(1, 300)
        self.cook_spin.setValue(20)

        cook_button = QPushButton("制作肠粉并写入出餐仓")
        cook_button.clicked.connect(self._cook)

        grid.addWidget(self.egg_check, 0, 0)
        grid.addWidget(self.shrimp_check, 0, 1)
        grid.addWidget(QLabel("烹饪时长(秒):"), 1, 0)
        grid.addWidget(self.cook_spin, 1, 1)
        grid.addWidget(self.edible_check, 2, 0)
        grid.addWidget(cook_button, 3, 0, 1, 2)

        root.addWidget(hint)
        root.addLayout(grid)
        root.addStretch(1)

    def _cook(self) -> None:
        """把当前勾选项记录为一份肠粉菜。"""
        keys = ["rice_batter"]
        if self.egg_check.isChecked():
            keys.append("egg")
        if self.shrimp_check.isChecked():
            keys.append("shrimp")

        self.workbench.add_prepared_dishes(
            station="cheung_fun",
            ingredient_keys=keys,
            edible=self.edible_check.isChecked(),
            cook_seconds=float(self.cook_spin.value()),
            quantity=1,
        )


class StapleTab(QWidget):
    """主食后台控件；批量记录米饭。"""

    def __init__(self, workbench: WorkbenchPage) -> None:
        super().__init__()
        self.workbench = workbench

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        hint = QLabel("主食固定为米饭（水+米），可一次制作多份。")
        hint.setStyleSheet("color: #475569;")

        form = QFormLayout()

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 20)
        self.quantity_spin.setValue(1)

        self.cook_spin = QSpinBox()
        self.cook_spin.setRange(1, 300)
        self.cook_spin.setValue(50)

        self.edible_check = QCheckBox("可食用")
        self.edible_check.setChecked(True)

        cook_button = QPushButton("煮饭并写入出餐仓")
        cook_button.clicked.connect(self._cook)

        form.addRow("份数:", self.quantity_spin)
        form.addRow("烹饪时长(秒):", self.cook_spin)
        form.addRow("状态:", self.edible_check)
        form.addRow(cook_button)

        root.addWidget(hint)
        root.addLayout(form)
        root.addStretch(1)

    def _cook(self) -> None:
        """把米和水记录为指定份数的主食。"""
        self.workbench.add_prepared_dishes(
            station="staple",
            ingredient_keys=["rice", "water"],
            edible=self.edible_check.isChecked(),
            cook_seconds=float(self.cook_spin.value()),
            quantity=self.quantity_spin.value(),
        )


class BbqTab(QWidget):
    """烧烤后台控件；批量记录同款烤串。"""

    def __init__(self, workbench: WorkbenchPage) -> None:
        super().__init__()
        self.workbench = workbench

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        hint = QLabel("烧烤单默认需要孜然；可选辣椒。每次可批量出同款烤串。")
        hint.setStyleSheet("color: #475569;")

        form = QFormLayout()

        self.skewer_combo = QComboBox()
        for key in BBQ_SKEWER_KEYS:
            self.skewer_combo.addItem(CATALOG[key].name, key)

        self.add_chili_check = QCheckBox("加辣椒")

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 20)
        self.quantity_spin.setValue(1)

        self.cook_spin = QSpinBox()
        self.cook_spin.setRange(1, 300)
        self.cook_spin.setValue(35)

        self.edible_check = QCheckBox("可食用")
        self.edible_check.setChecked(True)

        cook_button = QPushButton("出串并写入出餐仓")
        cook_button.clicked.connect(self._cook)

        form.addRow("烤串类型:", self.skewer_combo)
        form.addRow("调味:", self.add_chili_check)
        form.addRow("份数:", self.quantity_spin)
        form.addRow("烹饪时长(秒):", self.cook_spin)
        form.addRow("状态:", self.edible_check)
        form.addRow(cook_button)

        root.addWidget(hint)
        root.addLayout(form)
        root.addStretch(1)

    def _cook(self) -> None:
        """把当前烤串和调味选项记录进出餐仓。"""
        keys = [self.skewer_combo.currentData(), "cumin"]
        if self.add_chili_check.isChecked():
            keys.append("chili")

        self.workbench.add_prepared_dishes(
            station="bbq",
            ingredient_keys=keys,
            edible=self.edible_check.isChecked(),
            cook_seconds=float(self.cook_spin.value()),
            quantity=self.quantity_spin.value(),
        )


class CounterTab(QWidget):
    """点餐台后台控件；查看订单、预览匹配状态并出餐。"""

    def __init__(self, workbench: WorkbenchPage) -> None:
        super().__init__()
        self.workbench = workbench

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        tip = QLabel("系统每秒会推进点餐时间，订单每 20-30 秒生成。")
        tip.setStyleSheet("color: #475569;")

        top_bar = QHBoxLayout()
        self.refresh_button = QPushButton("刷新订单")
        self.refresh_button.clicked.connect(self.refresh_orders)

        self.serve_button = QPushButton("出餐当前订单")
        self.serve_button.clicked.connect(self._serve_selected)

        top_bar.addWidget(self.refresh_button)
        top_bar.addWidget(self.serve_button)
        top_bar.addStretch(1)

        content = QHBoxLayout()
        self.order_list = QListWidget()
        self.order_list.setMinimumWidth(320)
        self.order_list.itemSelectionChanged.connect(self._update_details)

        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)

        content.addWidget(self.order_list)
        content.addWidget(self.detail_view, 1)

        root.addWidget(tip)
        root.addLayout(top_bar)
        root.addLayout(content)

        self.refresh_orders()

    def selected_order_id(self) -> int | None:
        """返回当前选中的订单号。"""
        item = self.order_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        if value is None:
            return None
        return int(value)

    def refresh_orders(self) -> None:
        """从 `GameService` 读取活动订单并刷新列表。"""
        selected_id = self.selected_order_id()
        orders = self.workbench.service.get_active_orders()

        self.order_list.blockSignals(True)
        self.order_list.clear()

        selected_item: QListWidgetItem | None = None
        for order in orders:
            order_id = int(order["order_id"])
            remaining = self.workbench.service.get_order_remaining_seconds(order_id)
            text = f"#{order_id} {order['customer_name']} | 剩余 {remaining:.0f}s"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, order_id)
            self.order_list.addItem(item)
            if selected_id is not None and order_id == selected_id:
                selected_item = item

        if selected_item is not None:
            self.order_list.setCurrentItem(selected_item)
        elif self.order_list.count() > 0:
            self.order_list.setCurrentRow(0)

        self.order_list.blockSignals(False)
        self._update_details()

    def _update_details(self) -> None:
        """刷新右侧订单详情和出餐按钮状态。"""
        order_id = self.selected_order_id()
        if order_id is None:
            self.detail_view.setPlainText("暂无订单。")
            self.serve_button.setEnabled(False)
            return

        order = self.workbench.service.get_order_by_id(order_id)
        if order is None:
            self.detail_view.setPlainText("订单不存在或已结束。")
            self.serve_button.setEnabled(False)
            return

        remaining = self.workbench.service.get_order_remaining_seconds(order_id)
        lines = self.workbench.service.build_order_lines(order_id)
        preview = self.workbench.service.preview_order_match(order_id)

        detail: list[str] = [
            f"订单号: #{order_id}",
            f"顾客: {order['customer_name']}",
            f"剩余时间: {remaining:.1f}s",
            f"基础成本: $ {float(order['base_cost']):.2f}",
            "",
            "需求清单:",
        ]
        detail.extend(f"- {line}" for line in lines)
        detail.extend(
            [
                "",
                "匹配状态:",
                f"- 可出餐: {'是' if preview['can_serve'] else '否'}",
                f"- 完全匹配: {'是' if preview['exact_match'] else '否'}",
                f"- 含不可食菜品: {'是' if preview['has_inedible'] else '否'}",
                (
                    "- 当前满足: "
                    f"{preview['matched_count']}/{preview['required_count']}"
                ),
            ]
        )

        self.detail_view.setPlainText("\n".join(detail))
        self.serve_button.setEnabled(bool(preview.get("can_serve", False)))

    def _serve_selected(self) -> None:
        """后台出餐按钮入口；实际结算由 `GameService.serve_order()` 完成。"""
        order_id = self.selected_order_id()
        if order_id is None:
            QMessageBox.information(self, "提示", "请先选择一个订单。")
            return

        success, message, _income = self.workbench.service.serve_order(order_id)
        self.workbench.notify_message(message, success=success)
        self.workbench.refresh_status()
        self.refresh_orders()
