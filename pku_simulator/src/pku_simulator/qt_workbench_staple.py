"""主食/电饭煲工作台的状态逻辑。

拖拽米和水的入口在 `qt_workbench_drops.py`，电饭煲点击与开始/出锅按钮由
`qt_click_router.py` 转发到这里。绘制层 `qt_overlays_workbench.py` 只读取这些
状态方法，不直接修改业务数据。
"""

from __future__ import annotations

import time
from typing import Any

from pku_simulator.qt_defs import *


class StapleStationMixin:
    """维护多个电饭煲的加料、蒸饭计时和出餐入库。"""

    def _reset_staple_station(self) -> None:
        """初始化或重置电饭煲槽位状态。"""
        self.visible_staple_info_cookers.clear()
        self.staple_cookers = [
            {
                "has_rice": False,
                "has_water": False,
                "started_at": None,
                "done": False,
            }
            for _ in STAPLE_COOKER_SLOT_ASSET_NAMES
        ]


    def _staple_cooker_state(self, cooker_index: int) -> dict[str, Any]:
        """归一化单个电饭煲状态，兼容旧存档或异常值。"""
        cooker = self.staple_cookers[cooker_index]
        if isinstance(cooker, dict):
            cooker.setdefault("has_rice", False)
            cooker.setdefault("has_water", False)
            cooker.setdefault("started_at", None)
            cooker.setdefault("done", False)
            return cooker

        normalized = {
            "has_rice": False,
            "has_water": False,
            "started_at": None,
            "done": False,
        }
        self.staple_cookers[cooker_index] = normalized
        return normalized


    def staple_cooker_state_name(self, cooker_index: int) -> str:
        """返回 overlay 使用的状态名：empty/rice/water/ready/cooking/done。"""
        if not 0 <= cooker_index < len(self.staple_cookers):
            return "empty"
        cooker = self._staple_cooker_state(cooker_index)
        if bool(cooker.get("done", False)):
            return "done"
        if cooker.get("started_at") is not None:
            if self.staple_cooker_elapsed(cooker_index) >= STAPLE_RICE_COOK_SECONDS:
                cooker["done"] = True
                return "done"
            return "cooking"
        if bool(cooker.get("has_rice", False)) and bool(cooker.get("has_water", False)):
            return "ready"
        if bool(cooker.get("has_rice", False)):
            return "rice"
        if bool(cooker.get("has_water", False)):
            return "water"
        return "empty"


    def staple_cooker_elapsed(self, cooker_index: int) -> float:
        """返回电饭煲开始蒸饭后的秒数，供进度条和完成判断使用。"""
        if not 0 <= cooker_index < len(self.staple_cookers):
            return 0.0
        started_at = self._staple_cooker_state(cooker_index).get("started_at")
        if started_at is None:
            return 0.0
        try:
            return max(0.0, time.monotonic() - float(started_at))
        except (TypeError, ValueError):
            return 0.0


    def add_staple_ingredient_to_cooker(self, cooker_index: int, item_key: str) -> tuple[bool, str]:
        """拖拽米/水到电饭煲时调用：校验状态、扣库存、刷新画面。"""
        if item_key not in {"rice", "water"}:
            return False, "这个食材不能放进电饭煲。"
        if not 0 <= cooker_index < len(self.staple_cookers):
            return False, "没有放到电饭煲区域。"

        cooker = self._staple_cooker_state(cooker_index)
        if bool(cooker.get("done", False)) or cooker.get("started_at") is not None:
            return False, "这个电饭煲正在使用，不能继续加料。"
        if item_key == "rice" and bool(cooker.get("has_rice", False)):
            return False, "这个电饭煲已经有米了。"
        if item_key == "water" and bool(cooker.get("has_water", False)):
            return False, "这个电饭煲已经有水了。"

        success, message = self.service.consume_ingredient(item_key, 1)
        if not success:
            return False, message

        if item_key == "rice":
            cooker["has_rice"] = True
            message = f"已向第 {cooker_index + 1} 个电饭煲加入米。"
        else:
            cooker["has_water"] = True
            message = f"已向第 {cooker_index + 1} 个电饭煲加入水。"
        self.refresh_status()
        self.refresh_station_assets()
        return True, message


    def toggle_staple_info_panel(self, cooker_index: int) -> tuple[bool, str]:
        """点击电饭煲时展开/收起操作面板，空煲不展示面板。"""
        if not 0 <= cooker_index < len(self.staple_cookers):
            return False, "电饭煲不存在。"

        cooker = self._staple_cooker_state(cooker_index)
        if not (
            bool(cooker.get("has_rice", False))
            or bool(cooker.get("has_water", False))
            or cooker.get("started_at") is not None
            or bool(cooker.get("done", False))
        ):
            self.visible_staple_info_cookers.discard(cooker_index)
            return True, ""

        if cooker_index in self.visible_staple_info_cookers:
            self.visible_staple_info_cookers.remove(cooker_index)
        else:
            self.visible_staple_info_cookers.add(cooker_index)
        return True, ""


    def start_staple_cooker(self, cooker_index: int) -> tuple[bool, str]:
        """信息面板“开始蒸饭”按钮入口。"""
        if not 0 <= cooker_index < len(self.staple_cookers):
            return False, "电饭煲不存在。"

        cooker = self._staple_cooker_state(cooker_index)
        if bool(cooker.get("done", False)):
            return False, "米饭已经蒸好了。"
        if cooker.get("started_at") is not None:
            return True, "米饭正在蒸。"
        if bool(cooker.get("has_rice", False)) and bool(cooker.get("has_water", False)):
            cooker["started_at"] = time.monotonic()
            cooker["done"] = False
            self.refresh_station_assets()
            return True, f"第 {cooker_index + 1} 个电饭煲开始蒸饭。"

        if bool(cooker.get("has_rice", False)):
            return False, "还需要加水。"
        if bool(cooker.get("has_water", False)):
            return False, "还需要加米。"
        return False, "这个电饭煲还是空的。"


    def finish_staple_cooker(self, cooker_index: int) -> tuple[bool, str]:
        """信息面板“出锅”按钮入口，把米饭写入成品餐库。"""
        if not 0 <= cooker_index < len(self.staple_cookers):
            return False, "电饭煲不存在。"

        cooker = self._staple_cooker_state(cooker_index)
        if not bool(cooker.get("done", False)):
            return False, "米饭还没有蒸好。"

        self.service.record_prepared_dish(
            "staple",
            ["rice", "water"],
            True,
            self.staple_cooker_elapsed(cooker_index),
        )
        cooker["has_rice"] = False
        cooker["has_water"] = False
        cooker["started_at"] = None
        cooker["done"] = False
        self.visible_staple_info_cookers.discard(cooker_index)
        self.refresh_status()
        self.counter_tab.refresh_orders()
        self.refresh_station_assets()
        return True, f"第 {cooker_index + 1} 个电饭煲的米饭已进入餐库。"


    def update_staple_cookers(self) -> bool:
        """每次重绘主食台时推进计时状态，返回是否有电饭煲刚完成。"""
        changed = False
        for index in range(len(self.staple_cookers)):
            cooker = self._staple_cooker_state(index)
            if cooker.get("started_at") is None or bool(cooker.get("done", False)):
                continue
            if self.staple_cooker_elapsed(index) >= STAPLE_RICE_COOK_SECONDS:
                cooker["done"] = True
                changed = True
        return changed
