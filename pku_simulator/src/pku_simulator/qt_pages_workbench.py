"""营业区后台页面和站点协调器。

`WorkbenchPage` 同时继承四个工作台 mixin，保存各工作台的运行状态，并通过
`scene_changed` 通知主窗口切换 `GameSceneView` 的 scene。后台标签页来自
`qt_workbench_tabs.py`，图形玩法则通过覆盖层和拖拽信号驱动。
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from pku_simulator.core.catalog import CATALOG
from pku_simulator.qt_scene import BasePage
from pku_simulator.qt_workbench_bbq import BbqStationMixin
from pku_simulator.qt_workbench_cheung_fun import CheungFunStationMixin
from pku_simulator.qt_workbench_griddle import GriddleStationMixin
from pku_simulator.qt_workbench_staple import StapleStationMixin
from pku_simulator.qt_workbench_tabs import (
    BbqTab,
    CheungFunTab,
    CounterTab,
    GriddleTab,
    StapleTab,
)


class WorkbenchPage(
    GriddleStationMixin,
    CheungFunStationMixin,
    StapleStationMixin,
    BbqStationMixin,
    BasePage,
):
    """营业区总控页面。

    公开给其它模块的接口包括：
    - `current_scene_key()/switch_to_scene()`：底部导航/后台标签切换。
    - `add_prepared_dishes()`：后台控件直接写出餐仓。
    - 各工作台 mixin 方法：图形拖拽和覆盖层按钮调用。
    """

    scene_changed = Signal(str)

    TAB_SCENE_KEYS = [
        "griddle_station",
        "cheung_fun_station",
        "staple_station",
        "bbq_station",
        "counter_station",
    ]
    TAB_DOCK_ITEMS = [
        ("griddle_station", "烤", "烤盘间"),
        ("cheung_fun_station", "肠", "肠粉台"),
        ("staple_station", "饭", "主食区"),
        ("bbq_station", "串", "烧烤架"),
        ("counter_station", "单", "点餐台"),
        ("shop", "店", "商店"),
    ]

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)

        self._last_loaded_day = self.state.day
        self._auto_finish_day_triggered = False
        self.visible_griddle_info_pans: set[int] = set()
        self.visible_cheung_fun_info_pans: set[int] = set()
        self.griddle_pans: list[dict[str, Any]] = []
        self._reset_griddle_pans()
        self.cheung_fun_spoon_filled = False
        self.cheung_fun_pans: list[dict[str, Any]] = []
        self._reset_cheung_fun_station()
        self.bbq_slots: list[dict[str, Any] | None] = []
        self.visible_bbq_info_slots: set[int] = set()
        self._reset_bbq_station()
        self.staple_cookers: list[dict[str, Any]] = []
        self.visible_staple_info_cookers: set[int] = set()
        self._reset_staple_station()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        header = QHBoxLayout()

        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 14px; color: #334155;")

        self.end_day_button = QPushButton("收餐结算")
        self.end_day_button.setFixedHeight(38)
        self.end_day_button.setStyleSheet(
            "QPushButton {"
            "background-color: #be123c;"
            "color: white;"
            "border-radius: 8px;"
            "padding: 6px 16px;"
            "font-size: 14px;"
            "font-weight: 600;"
            "}"
            "QPushButton:hover { background-color: #9f1239; }"
        )
        self.end_day_button.clicked.connect(self._finish_day)

        header.addWidget(self.status_label)
        header.addStretch(1)
        header.addWidget(self.end_day_button)

        self.message_label = QLabel("已进入营业区。")
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("font-size: 14px; color: #334155;")

        self.tabs = QTabWidget()
        self.griddle_tab = GriddleTab(self)
        self.cheung_fun_tab = CheungFunTab(self)
        self.staple_tab = StapleTab(self)
        self.bbq_tab = BbqTab(self)
        self.counter_tab = CounterTab(self)

        self.tabs.addTab(self.griddle_tab, "烤盘间")
        self.tabs.addTab(self.cheung_fun_tab, "肠粉台")
        self.tabs.addTab(self.staple_tab, "主食区")
        self.tabs.addTab(self.bbq_tab, "烧烤架")
        self.tabs.addTab(self.counter_tab, "点餐台")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        root.addLayout(header)
        root.addWidget(self.message_label)
        root.addWidget(self.tabs)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_orders)

        self._griddle_info_timer = QTimer(self)
        self._griddle_info_timer.setInterval(100)
        self._griddle_info_timer.timeout.connect(self._tick_griddle_info)

    def on_enter(self) -> None:
        """进入营业区时恢复/重置站点状态并启动订单计时器。"""
        if self._last_loaded_day != self.state.day:
            self._last_loaded_day = self.state.day
            self._auto_finish_day_triggered = False
            self._reset_griddle_pans()
            self._reset_cheung_fun_station()
            self._reset_bbq_station()
            self._reset_staple_station()
        self.refresh_status()
        self.counter_tab.refresh_orders()
        self._timer.start()
        self._griddle_info_timer.start()
        self.refresh_station_assets()

    def on_exit(self) -> None:
        """离开营业区时暂停订单和工位刷新计时器。"""
        self._timer.stop()
        self._griddle_info_timer.stop()

    def refresh_status(self) -> None:
        """刷新后台状态栏：天数、余额和出餐仓数量。"""
        self.status_label.setText(
            (
                f"第 {self.state.day} 天 | 余额: $ {self.state.balance:.2f} | "
                f"出餐仓: {self.service.prepared_dish_count()}"
            )
        )

    def notify_message(self, text: str, success: bool) -> None:
        """给后台页面显示一条操作提示；图形覆盖层也间接依赖它的状态刷新。"""
        color = "#166534" if success else "#9a3412"
        self.message_label.setStyleSheet(f"font-size: 14px; color: {color};")
        self.message_label.setText(text)

    def add_prepared_dishes(
        self,
        station: str,
        ingredient_keys: list[str],
        edible: bool,
        cook_seconds: float,
        quantity: int = 1,
    ) -> None:
        """后台控件快速出餐入口；图形玩法通常走各工作台 finish 方法。"""
        if quantity <= 0:
            self.notify_message("数量必须大于 0。", success=False)
            return
        if not ingredient_keys:
            self.notify_message("至少需要一种食材。", success=False)
            return

        for _ in range(quantity):
            self.service.record_prepared_dish(station, ingredient_keys, edible, cook_seconds)

        name_counts = Counter(
            CATALOG[key].name if key in CATALOG else key
            for key in ingredient_keys
        )
        desc = "、".join(
            f"{name}x{count}" if count > 1 else name
            for name, count in name_counts.items()
        )
        suffix = f"，共 {quantity} 份" if quantity > 1 else ""
        self.notify_message(f"已出餐: {desc}{suffix}", success=True)

        self.refresh_status()
        self.counter_tab.refresh_orders()

    def _tick_orders(self) -> None:
        """每秒推进点餐台订单，并同步后台列表和图形覆盖层。"""
        events = self.service.tick_counter_orders(1.0)
        if events["cancelled"]:
            total_penalty = sum(item["penalty"] for item in events["cancelled"])
            self.notify_message(f"有订单超时，自动赔付 $ {total_penalty:.2f}", success=False)
        elif events["new_orders"]:
            self.notify_message(f"新增 {len(events['new_orders'])} 条订单。", success=True)

        self.refresh_status()
        self.counter_tab.refresh_orders()
        self.main_window.sync_counter_orders()
        self.main_window.refresh_order_taunt_overlay()
        self._maybe_auto_finish_day()
        if self.current_scene_key() == "griddle_station":
            self.refresh_station_assets()
        if self.current_scene_key() == "counter_station":
            self.refresh_station_assets()

    def _tick_griddle_info(self) -> None:
        """高频刷新工作台信息框/进度条，并处理过火损坏。"""
        current_scene_key = self.current_scene_key()
        is_griddle_scene = current_scene_key == "griddle_station"
        expired = self._expire_overcooked_griddle_pans()

        if current_scene_key == "cheung_fun_station":
            expired = self._expire_overcooked_cheung_fun_pans()
            if expired or self.visible_cheung_fun_info_pans:
                self.refresh_station_assets()
            return

        if current_scene_key == "bbq_station":
            self.refresh_station_assets()
            return

        if current_scene_key == "counter_station":
            self.refresh_station_assets()
            return

        if current_scene_key == "staple_station":
            self.refresh_station_assets()
            return

        if not is_griddle_scene:
            return
        if expired:
            self.main_window.game_scene_view.reload_scene()
        elif self.visible_griddle_info_pans:
            self.refresh_station_assets()

    def _finish_day(self) -> None:
        """手动或自动收餐，按服务层结果切到失败页或下一天开始页。"""
        self._auto_finish_day_triggered = True
        game_over = self.service.finish_day()
        if game_over:
            self.main_window.change_screen("game_over")
        else:
            self.main_window.change_screen("start")

    def _maybe_auto_finish_day(self) -> None:
        """无新顾客且无未完成订单时自动触发收餐。"""
        if self._auto_finish_day_triggered:
            return
        if not self.service.should_auto_finish_service_day():
            return

        self._auto_finish_day_triggered = True
        self.notify_message("今日营业结束，正在收餐结算。", success=True)
        QTimer.singleShot(0, self._finish_day)

    def refresh_station_assets(self) -> None:
        """通知主窗口刷新当前工作台场景和覆盖层。"""
        self.scene_changed.emit(self.current_scene_key())

    def current_scene_key(self) -> str:
        """把后台标签索引映射成图形场景 key。"""
        index = self.tabs.currentIndex()
        if 0 <= index < len(self.TAB_SCENE_KEYS):
            return self.TAB_SCENE_KEYS[index]
        return self.TAB_SCENE_KEYS[0]

    def switch_to_scene(self, scene_key: str) -> bool:
        """底部图形导航调用；成功后后台标签也同步切换。"""
        if scene_key not in self.TAB_SCENE_KEYS:
            return False
        self.tabs.setCurrentIndex(self.TAB_SCENE_KEYS.index(scene_key))
        return True

    def _on_tab_changed(self, _index: int) -> None:
        self.refresh_station_assets()
