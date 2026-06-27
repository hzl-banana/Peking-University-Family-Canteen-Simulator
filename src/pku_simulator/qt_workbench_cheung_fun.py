"""肠粉工作台的状态逻辑。

这里负责面糊勺、四个肠粉烤台、配料熟度、爆炸损坏和出锅入库。
拖拽/点击接口分别来自 `qt_workbench_drops.py` 和 `qt_click_router.py`，
overlay 只通过这些方法读取状态或触发动作。
"""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QTimer

from pku_simulator.core.catalog import CATALOG
from pku_simulator.core.save_repo import save_state
from pku_simulator.qt_defs import *


class CheungFunStationMixin:
    """维护肠粉烤台状态，并把完成的肠粉写入成品餐库。"""

    def _reset_cheung_fun_station(self) -> None:
        """按当天损坏记录初始化肠粉烤台和面糊勺。"""
        self.visible_cheung_fun_info_pans.clear()
        self.cheung_fun_spoon_filled = False
        broken_count = max(0, min(4, int(self.state.broken_stations.get("cheung_fun", 0))))
        self.cheung_fun_pans = [
            {
                "has_batter": False,
                "ingredients": [],
                "finished": False,
                "exploded": index < broken_count,
                "started_at": None,
            }
            for index in range(4)
        ]


    def fill_cheung_fun_spoon(self) -> tuple[bool, str]:
        """点击/拖动面糊勺入口：把勺子置为可倒面糊状态。"""
        self.cheung_fun_spoon_filled = True
        self.refresh_station_assets()
        return True, "面糊勺已装满。"


    def pour_cheung_fun_batter_to_pan(self, pan_index: int) -> tuple[bool, str]:
        """把已装满的面糊勺倒到指定烤台，启动面糊计时。"""
        if not 0 <= pan_index < len(self.cheung_fun_pans):
            return False, "没有放到烤台区域。"
        if not self.cheung_fun_spoon_filled:
            return False, "面糊勺还是空的。"

        pan = self._cheung_fun_pan_state(pan_index)
        if bool(pan.get("exploded", False)):
            return False, f"第 {pan_index + 1} 个肠粉烤台已炸坏，今天不能继续使用。"
        pan["has_batter"] = True
        pan["ingredients"] = []
        pan["finished"] = False
        pan["exploded"] = False
        pan["started_at"] = time.monotonic()
        self.cheung_fun_spoon_filled = False
        self.refresh_station_assets()
        return True, f"已在第 {pan_index + 1} 个烤台铺上肠粉。"


    def _cheung_fun_pan_state(self, pan_index: int) -> dict[str, Any]:
        """归一化单个肠粉烤台状态，避免旧格式影响绘制和业务判断。"""
        pan = self.cheung_fun_pans[pan_index]
        if isinstance(pan, dict):
            pan.setdefault("has_batter", False)
            pan.setdefault("ingredients", [])
            pan.setdefault("finished", False)
            pan.setdefault("exploded", False)
            pan.setdefault("started_at", None)
            return pan

        normalized = {
            "has_batter": bool(pan),
            "ingredients": [],
            "finished": False,
            "exploded": False,
            "started_at": time.monotonic() if pan else None,
        }
        self.cheung_fun_pans[pan_index] = normalized
        return normalized


    def _cheung_fun_ingredient_entries(self, pan: dict[str, Any]) -> list[dict[str, Any]]:
        """把配料列表统一为 `{key, added_at}`，供熟度/爆炸判断复用。"""
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


    def _break_cheung_fun_pan(self, pan_index: int, pan: dict[str, Any]) -> None:
        """把过熟爆炸后的烤台标记为当天不可用，并同步损坏计数。"""
        pan["has_batter"] = False
        pan["ingredients"] = []
        pan["finished"] = False
        pan["exploded"] = True
        pan["started_at"] = None
        self.visible_cheung_fun_info_pans.discard(pan_index)
        self.state.broken_stations["cheung_fun"] = (
            int(self.state.broken_stations.get("cheung_fun", 0)) + 1
        )


    def _expire_overcooked_cheung_fun_pans(self) -> bool:
        """定时扫描配料是否过熟爆炸；发生变化时保存当天损坏状态。"""
        changed = False
        now = time.monotonic()

        for index, pan in enumerate(self.cheung_fun_pans):
            pan = self._cheung_fun_pan_state(index)
            if bool(pan.get("exploded", False)):
                continue

            ingredient_entries = self._cheung_fun_ingredient_entries(pan)
            if not ingredient_entries:
                continue

            if not any(
                now - float(entry["added_at"]) > CHEUNG_FUN_OVERCOOK_SECONDS
                for entry in ingredient_entries
            ):
                continue

            self._break_cheung_fun_pan(index, pan)
            changed = True

        if changed:
            self.refresh_status()
            save_state(self.state)

        return changed


    def add_cheung_fun_ingredient_to_pan(self, pan_index: int, item_key: str) -> tuple[bool, str]:
        """拖拽鸡蛋/虾到肠粉台时调用：扣库存并记录投料时间。"""
        if item_key not in {"egg", "shrimp"}:
            return False, "这个食材暂时不能加进肠粉。"
        if not 0 <= pan_index < len(self.cheung_fun_pans):
            return False, "没有放到肠粉区域。"

        pan = self._cheung_fun_pan_state(pan_index)
        if bool(pan.get("exploded", False)):
            return False, f"第 {pan_index + 1} 个肠粉烤台已炸坏，今天不能继续使用。"
        if not bool(pan.get("has_batter", False)):
            return False, "这个烤台上还没有肠粉。"
        if bool(pan.get("finished", False)):
            return False, "这份肠粉已经做好了，不能再加料。"

        success, message = self.service.consume_ingredient(item_key, 1)
        if not success:
            return False, message

        ingredients = pan.setdefault("ingredients", [])
        if not isinstance(ingredients, list):
            ingredients = []
            pan["ingredients"] = ingredients
        now = time.monotonic()
        ingredients.append({"key": item_key, "added_at": now})
        if pan.get("started_at") is None:
            pan["started_at"] = now
        self.refresh_status()
        self.refresh_station_assets()
        return True, f"已给第 {pan_index + 1} 份肠粉加入{CATALOG[item_key].name}。"


    def stir_cheung_fun_pan(self, pan_index: int) -> tuple[bool, str]:
        """炒勺操作入口：检查面糊和配料熟度，熟了才标记为可出锅。"""
        if not 0 <= pan_index < len(self.cheung_fun_pans):
            return False, "没有放到肠粉区域。"

        pan = self._cheung_fun_pan_state(pan_index)
        if bool(pan.get("exploded", False)):
            return False, f"第 {pan_index + 1} 个肠粉烤台已炸坏，今天不能继续使用。"
        if not bool(pan.get("has_batter", False)):
            return False, "这个烤台上还没有肠粉。"
        if bool(pan.get("finished", False)):
            return True, "这份肠粉已经是成品。"

        ingredient_entries = self._cheung_fun_ingredient_entries(pan)
        now = time.monotonic()
        exploded_entries = [
            entry
            for entry in ingredient_entries
            if now - float(entry["added_at"]) > CHEUNG_FUN_OVERCOOK_SECONDS
        ]
        if exploded_entries:
            self._break_cheung_fun_pan(pan_index, pan)
            save_state(self.state)
            self.refresh_status()
            self.refresh_station_assets()
            return False, "配料已经爆炸，烤台今天无法继续使用。"

        raw_entries = [
            entry
            for entry in ingredient_entries
            if now - float(entry["added_at"]) < _griddle_cook_seconds_for_key(str(entry["key"]))
        ]
        if raw_entries:
            return False, "配料还没熟。"
        started_at = pan.get("started_at")
        try:
            batter_elapsed = max(0.0, now - float(started_at))
        except (TypeError, ValueError):
            batter_elapsed = 0.0
        if batter_elapsed < CHEUNG_FUN_BATTER_COOK_SECONDS:
            return False, "面糊还没熟。"

        pan["finished"] = True
        self.refresh_station_assets()
        return True, f"第 {pan_index + 1} 份肠粉已经做好，可以出锅。"


    def toggle_cheung_fun_info_panel(self, pan_index: int) -> tuple[bool, str]:
        """点击肠粉台时展开/收起信息面板；空台或坏台不展示可操作面板。"""
        if not 0 <= pan_index < len(self.cheung_fun_pans):
            return False, "肠粉烤台不存在。"

        pan = self._cheung_fun_pan_state(pan_index)
        if bool(pan.get("exploded", False)):
            self.visible_cheung_fun_info_pans.discard(pan_index)
            return False, "这个肠粉烤台已经炸坏，明天会自动维修。"
        if not bool(pan.get("has_batter", False)):
            self.visible_cheung_fun_info_pans.discard(pan_index)
            return True, ""

        if pan_index in self.visible_cheung_fun_info_pans:
            self.visible_cheung_fun_info_pans.remove(pan_index)
        else:
            self.visible_cheung_fun_info_pans.add(pan_index)
        return True, ""


    def finish_cheung_fun_pan(self, pan_index: int) -> tuple[bool, str]:
        """信息面板“出锅”入口，把完成的肠粉写入成品餐库并刷新订单。"""
        if not 0 <= pan_index < len(self.cheung_fun_pans):
            return False, "肠粉烤台不存在。"

        pan = self._cheung_fun_pan_state(pan_index)
        if bool(pan.get("exploded", False)):
            return False, f"第 {pan_index + 1} 个肠粉烤台已炸坏，今天不能继续使用。"
        if not bool(pan.get("has_batter", False)):
            return False, "这个烤台上还没有肠粉。"
        if not bool(pan.get("finished", False)):
            return False, "还没有用炒勺完成肠粉。"

        ingredient_entries = self._cheung_fun_ingredient_entries(pan)
        now = time.monotonic()
        if any(
            now - float(entry["added_at"]) > CHEUNG_FUN_OVERCOOK_SECONDS
            for entry in ingredient_entries
        ):
            self._break_cheung_fun_pan(pan_index, pan)
            save_state(self.state)
            self.refresh_status()
            self.refresh_station_assets()
            return False, "配料已经爆炸，烤台今天无法继续使用。"

        extras = [str(entry["key"]) for entry in ingredient_entries]
        ingredient_keys = ["rice_batter", *extras]
        started_at = pan.get("started_at")
        try:
            cook_seconds = max(0.0, time.monotonic() - float(started_at))
        except (TypeError, ValueError):
            cook_seconds = 0.0

        self.state.prepared_dishes.append(
            {
                "day": self.state.day,
                "station": "cheung_fun",
                "ingredient_keys": ingredient_keys,
                "edible": True,
                "cook_seconds": round(cook_seconds, 2),
            }
        )
        pan["has_batter"] = False
        pan["ingredients"] = []
        pan["finished"] = False
        pan["started_at"] = None
        self.visible_cheung_fun_info_pans.discard(pan_index)

        self.refresh_status()
        self.counter_tab.refresh_orders()
        QTimer.singleShot(50, lambda state=self.state: save_state(state))
        self.refresh_station_assets()
        return True, f"第 {pan_index + 1} 份肠粉已出锅。"
