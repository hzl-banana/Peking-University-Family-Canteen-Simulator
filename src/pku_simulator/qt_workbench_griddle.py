"""煎扒/烤盘工作台的状态逻辑。

这个 mixin 处理烤盘投料、烹饪计时、过熟损坏和出锅入库。UI 投料来自
`GameSceneView` 的拖拽信号，点击面板来自 `qt_click_router.py`，成品会被
点餐台服务用于订单匹配。
"""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QTimer

from pku_simulator.core.catalog import CATALOG
from pku_simulator.core.save_repo import save_state
from pku_simulator.qt_defs import *


class GriddleStationMixin:
    """维护四个烤盘的食材列表、损坏状态和成品记录。"""

    def _reset_griddle_pans(self) -> None:
        """按存档中的损坏数量初始化当天烤盘状态。"""
        self.visible_griddle_info_pans.clear()
        broken_count = max(0, min(4, int(self.state.broken_stations.get("griddle", 0))))
        self.griddle_pans = []
        for index in range(4):
            self.griddle_pans.append(
                {
                    "ingredients": [],
                    "started_at": None,
                    "broken": index < broken_count,
                }
            )


    def _expire_overcooked_griddle_pans(self) -> bool:
        """定时检查过熟烤盘；过熟会清空食材、标记损坏并保存状态。"""
        changed = False

        for index, pan in enumerate(self.griddle_pans):
            if bool(pan.get("broken", False)):
                continue

            if not self._griddle_ingredient_entries(pan):
                continue

            if self.griddle_pan_elapsed(index) <= GRIDDLE_OVERCOOK_SECONDS:
                continue

            pan["ingredients"] = []
            pan["started_at"] = None
            pan["broken"] = True
            self.visible_griddle_info_pans.discard(index)
            self.state.broken_stations["griddle"] = (
                int(self.state.broken_stations.get("griddle", 0)) + 1
            )
            changed = True

        if changed:
            self.refresh_status()
            save_state(self.state)

        return changed


    def add_griddle_ingredient_to_pan(self, pan_index: int, item_key: str) -> tuple[bool, str]:
        """拖拽食材到烤盘时调用；这里登记投料时间并通知 tab 记录拖拽。"""
        if not 0 <= pan_index < len(self.griddle_pans):
            return False, "没有放到烤盘区域，食材已丢弃。"

        pan = self.griddle_pans[pan_index]
        if bool(pan.get("broken", False)):
            return False, f"第 {pan_index + 1} 个烤盘已损坏，食材已丢弃。"

        ingredients = pan.setdefault("ingredients", [])
        if not isinstance(ingredients, list):
            ingredients = []
            pan["ingredients"] = ingredients
        now = time.monotonic()
        ingredients.append({"key": item_key, "added_at": now})
        if pan.get("started_at") is None:
            pan["started_at"] = now

        self.griddle_tab.add_dragged_ingredient(item_key)
        return True, f"已放入第 {pan_index + 1} 个烤盘: {CATALOG[item_key].name}"


    def toggle_griddle_info_panel(self, pan_index: int) -> tuple[bool, str]:
        """点击烤盘时展开/收起烹饪进度面板。"""
        if not 0 <= pan_index < len(self.griddle_pans):
            return False, "烤盘不存在。"

        if bool(self.griddle_pans[pan_index].get("broken", False)):
            self.visible_griddle_info_pans.discard(pan_index)
            return False, "这个烤盘已经损坏。"

        ingredients = self.griddle_pans[pan_index].get("ingredients", [])
        if not ingredients:
            self.visible_griddle_info_pans.discard(pan_index)
            return True, ""

        if pan_index in self.visible_griddle_info_pans:
            self.visible_griddle_info_pans.remove(pan_index)
        else:
            self.visible_griddle_info_pans.add(pan_index)
        return True, ""


    def griddle_pan_elapsed(self, pan_index: int) -> float:
        """返回某个烤盘从第一份食材下锅起经过的秒数。"""
        if not 0 <= pan_index < len(self.griddle_pans):
            return 0.0
        started_at = self.griddle_pans[pan_index].get("started_at")
        if started_at is None:
            return 0.0
        return max(0.0, time.monotonic() - float(started_at))


    def finish_griddle_pan(self, pan_index: int) -> tuple[bool, str]:
        """信息面板“出锅”入口：根据熟度写入可食用或不可食用成品。"""
        if not 0 <= pan_index < len(self.griddle_pans):
            return False, "烤盘不存在。"

        pan = self.griddle_pans[pan_index]
        if bool(pan.get("broken", False)):
            return False, "这个烤盘已经损坏。"

        ingredient_entries = self._griddle_ingredient_entries(pan)
        ingredient_keys = [entry["key"] for entry in ingredient_entries]
        if not ingredient_keys:
            return False, "这个烤盘还是空的。"

        elapsed = self.griddle_pan_elapsed(pan_index)
        now = time.monotonic()
        edible = (
            elapsed <= GRIDDLE_OVERCOOK_SECONDS
            and all(
                now - entry["added_at"] >= _griddle_cook_seconds_for_key(entry["key"])
                for entry in ingredient_entries
            )
        )
        self.state.prepared_dishes.append(
            {
                "day": self.state.day,
                "station": "griddle",
                "ingredient_keys": ingredient_keys,
                "edible": edible,
                "cook_seconds": round(elapsed, 2),
            }
        )

        pan["ingredients"] = []
        pan["started_at"] = None
        self.visible_griddle_info_pans.discard(pan_index)

        if elapsed > GRIDDLE_OVERCOOK_SECONDS:
            pan["broken"] = True
            if "griddle" not in self.state.broken_stations:
                self.state.broken_stations["griddle"] = 0
            self.state.broken_stations["griddle"] += 1
            self.refresh_status()
            QTimer.singleShot(50, lambda state=self.state: save_state(state))
            return True, "烤盘超时出锅，食物不可食用，烤盘已损坏。"

        self.refresh_status()
        QTimer.singleShot(50, lambda state=self.state: save_state(state))
        return True, f"已出锅，烹饪 {elapsed:.0f} 秒。"


    def _griddle_ingredient_entries(self, pan: dict[str, Any]) -> list[dict[str, Any]]:
        """把烤盘食材列表规范成 `{key, added_at}`，供进度条和出锅判断共用。"""
        raw_ingredients = pan.get("ingredients", [])
        if not isinstance(raw_ingredients, list):
            pan["ingredients"] = []
            return []

        fallback_added_at = pan.get("started_at")
        if fallback_added_at is None:
            fallback_added_at = time.monotonic()

        entries: list[dict[str, Any]] = []
        changed = False
        for item in raw_ingredients:
            if isinstance(item, dict):
                key = str(item.get("key", "")).strip()
                added_at = item.get("added_at", fallback_added_at)
                try:
                    added_at_float = float(added_at)
                except (TypeError, ValueError):
                    added_at_float = float(fallback_added_at)
                    changed = True
            else:
                key = str(item).strip()
                added_at_float = float(fallback_added_at)
                changed = True

            if key:
                entries.append({"key": key, "added_at": added_at_float})

        if changed:
            pan["ingredients"] = entries
        return entries
