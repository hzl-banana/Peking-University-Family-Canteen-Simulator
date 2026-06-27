"""点餐台交互状态控制。

订单数据由 `GameService` 维护；这个 mixin 只保存“当前顾客动画/清单/挂单”
等 UI 状态，并把点餐覆盖层点击转成服务层调用。
"""

from __future__ import annotations

import time

from pku_simulator.qt_pages import WorkbenchPage


class CounterControllerMixin:
    """点餐台 UI 状态接口；由 `MainWindow` 继承并供覆盖层读取这些字段。"""

    def _setup_counter_state(self) -> None:
        """初始化点餐台覆盖层需要的临时状态。"""
        self._counter_active_customer_order_id: int | None = None
        self._counter_active_customer_started_at = 0.0
        self._counter_accept_prompt_order_id: int | None = None
        self._counter_active_ticket_started_at: float | None = None
        self._counter_active_ticket_lines: list[str] = []
        self._counter_zoomed_order_id: int | None = None
        self._counter_completed_order_ids: set[int] = set()
        self._counter_hang_started_at_by_order_id: dict[int, float] = {}

    def sync_counter_orders(self) -> None:
        """同步服务层订单和覆盖层状态，并在点餐台场景弹出下一位顾客。"""
        active_ids = {int(order["order_id"]) for order in self.service.get_active_orders()}
        self._counter_completed_order_ids.intersection_update(active_ids)
        self._counter_hang_started_at_by_order_id = {
            order_id: started_at
            for order_id, started_at in self._counter_hang_started_at_by_order_id.items()
            if order_id in active_ids
        }
        if self._counter_active_customer_order_id not in active_ids:
            self._counter_active_customer_order_id = None
            self._counter_accept_prompt_order_id = None
            self._counter_active_ticket_started_at = None
            self._counter_active_ticket_lines = []
        if self._counter_zoomed_order_id not in active_ids:
            self._counter_zoomed_order_id = None

        if self._current_name != "workbench":
            return

        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            return
        if workbench.current_scene_key() != "counter_station":
            return
        if self._counter_active_customer_order_id is not None:
            return

        next_order = self.service.pop_next_unannounced_order()
        if next_order is None:
            return

        order_id = int(next_order["order_id"])
        self._counter_active_customer_order_id = order_id
        self._counter_active_customer_started_at = time.monotonic()
        self._counter_accept_prompt_order_id = None
        self._counter_active_ticket_started_at = None
        self._counter_active_ticket_lines = []

    def _on_counter_customer_clicked(self, asset_name: str) -> None:
        """点击顾客后显示“接单”提示。"""
        order_id = self._parse_trailing_int(asset_name)
        if order_id is None or order_id != self._counter_active_customer_order_id:
            return
        if self._counter_active_ticket_started_at is None:
            self._counter_accept_prompt_order_id = order_id
            self.game_scene_view.refresh_overlay()

    def _on_counter_accept_clicked(self, asset_name: str) -> None:
        """点击接单后开始显示当前顾客清单文本。"""
        order_id = self._parse_trailing_int(asset_name)
        if order_id is None or order_id != self._counter_active_customer_order_id:
            return
        self._counter_accept_prompt_order_id = None
        self._counter_active_ticket_started_at = time.monotonic()
        self._counter_active_ticket_lines = self.service.build_order_lines(order_id)
        self.game_scene_view.refresh_overlay()

    def _on_counter_order_done_clicked(self, asset_name: str) -> None:
        """顾客清单读完后挂到顶部待出餐栏。"""
        order_id = self._parse_trailing_int(asset_name)
        if order_id is None or order_id != self._counter_active_customer_order_id:
            return
        self._counter_completed_order_ids.add(order_id)
        self._counter_hang_started_at_by_order_id[order_id] = time.monotonic()
        self._counter_active_customer_order_id = None
        self._counter_accept_prompt_order_id = None
        self._counter_active_ticket_started_at = None
        self._counter_active_ticket_lines = []
        self.sync_counter_orders()
        self.game_scene_view.refresh_overlay()

    def _on_counter_ticket_clicked(self, asset_name: str) -> None:
        """点击挂单清单后放大查看。"""
        order_id = self._parse_trailing_int(asset_name)
        if order_id is None:
            return
        if self.service.get_order_by_id(order_id) is None:
            self.sync_counter_orders()
            self.game_scene_view.refresh_overlay()
            return
        self._counter_zoomed_order_id = order_id
        self.game_scene_view.refresh_overlay()

    def _on_counter_serve_clicked(self, asset_name: str) -> None:
        """点击放大清单里的出餐按钮后调用 `GameService.serve_order()`。"""
        order_id = self._parse_trailing_int(asset_name)
        if order_id is None:
            return

        workbench = self._pages.get("workbench")
        success, message, _income = self.service.serve_order(order_id)
        if isinstance(workbench, WorkbenchPage):
            workbench.notify_message(message, success=success)
            workbench.refresh_status()
            workbench.counter_tab.refresh_orders()

        self._counter_completed_order_ids.discard(order_id)
        self._counter_hang_started_at_by_order_id.pop(order_id, None)
        if self._counter_zoomed_order_id == order_id:
            self._counter_zoomed_order_id = None
        self.sync_counter_orders()
        self.game_scene_view.refresh_overlay()

    def _parse_trailing_int(self, value: str) -> int | None:
        """解析形如 `counter_ticket:12` 的图形项 data。"""
        try:
            return int(value.rsplit(":", 1)[1])
        except (IndexError, ValueError):
            return None
