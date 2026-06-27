"""烧烤工作台的状态与业务动作。

本 mixin 被 `WorkbenchPage` 组合使用；`qt_workbench_drops.py` 会把拖拽投放
转成这里的 `add_bbq_skewer_to_slot()` / `season_bbq_slot()` 调用，
`qt_click_router.py` 则把烤串点击和出串按钮转到信息面板与完成动作。
"""

from __future__ import annotations

import time
from typing import Any

from pku_simulator.core.catalog import CATALOG
from pku_simulator.qt_defs import *


class BbqStationMixin:
    """维护烧烤槽位、调料状态和出餐入库流程。"""

    def _reset_bbq_station(self) -> None:
        """新营业日或页面初始化时重置所有烧烤槽位。"""
        self.visible_bbq_info_slots.clear()
        self.bbq_slots = [None for _ in BBQ_SLOT_ASSET_NAMES]


    def bbq_slot_state(self, slot_index: int) -> dict[str, Any] | None:
        """读取单个槽位状态；overlay 绘制与点击路由都会先走这个守卫。"""
        if not 0 <= slot_index < len(self.bbq_slots):
            return None
        slot = self.bbq_slots[slot_index]
        if slot is None:
            return None
        if not isinstance(slot, dict):
            self.bbq_slots[slot_index] = None
            return None
        return slot


    def add_bbq_skewer_to_slot(self, slot_index: int, item_key: str) -> tuple[bool, str]:
        """拖拽生烤串到烤架时调用：扣库存、启动计时并刷新画面。"""
        if item_key not in BBQ_RAW_SKEWER_ASSET_NAMES_BY_KEY:
            return False, "这个烤串暂时不能放到烧烤架。"
        if not 0 <= slot_index < len(self.bbq_slots):
            return False, "旁边没有可用的烧烤热区。"
        if self.bbq_slots[slot_index] is not None:
            return False, "这个小热区已经放了烤串。"

        success, message = self.service.consume_ingredient(item_key, 1)
        if not success:
            return False, message

        self.bbq_slots[slot_index] = {
            "key": item_key,
            "started_at": time.monotonic(),
            "has_cumin": True,
            "has_chili": False,
        }
        self.refresh_status()
        self.refresh_station_assets()
        return True, f"已放到烧烤架: {CATALOG[item_key].name}"


    def bbq_slot_elapsed(self, slot_index: int) -> float:
        """给 overlay 进度判断使用，返回槽位从开烤到现在的秒数。"""
        slot = self.bbq_slot_state(slot_index)
        if slot is None:
            return 0.0
        try:
            return max(0.0, time.monotonic() - float(slot.get("started_at", time.monotonic())))
        except (TypeError, ValueError):
            return 0.0


    def bbq_slot_cooked(self, slot_index: int) -> bool:
        """判断烤串是否达到可出串阈值。"""
        return self.bbq_slot_elapsed(slot_index) >= BBQ_SKEWER_COOK_SECONDS


    def toggle_bbq_info_slot(self, slot_index: int) -> tuple[bool, str]:
        """点击熟烤串时展开/收起出串面板；未熟或空槽位不显示面板。"""
        slot = self.bbq_slot_state(slot_index)
        if slot is None:
            self.visible_bbq_info_slots.discard(slot_index)
            return True, ""
        if not self.bbq_slot_cooked(slot_index):
            self.visible_bbq_info_slots.discard(slot_index)
            return True, ""
        if slot_index in self.visible_bbq_info_slots:
            self.visible_bbq_info_slots.remove(slot_index)
        else:
            self.visible_bbq_info_slots.add(slot_index)
        return True, ""


    def season_bbq_slot(self, slot_index: int, seasoning_key: str) -> tuple[bool, str]:
        """处理孜然/辣椒拖拽；slot_index 为负数时表示撒到所有已有烤串。"""
        if seasoning_key not in {"cumin", "chili"}:
            return False, "这个调料暂时不能用于烧烤。"

        target_indexes: list[int]
        if slot_index < 0:
            target_indexes = [
                index
                for index, slot in enumerate(self.bbq_slots)
                if slot is not None
            ]
        else:
            target_indexes = [slot_index]

        if not target_indexes:
            return False, "调料没有撒到烤串上。"

        updated = False
        for index in target_indexes:
            slot = self.bbq_slot_state(index)
            if slot is None:
                continue
            slot[f"has_{seasoning_key}"] = True
            updated = True

        if not updated:
            return False, "调料没有撒到烤串上。"

        self.refresh_station_assets()
        return True, "已加孜然。" if seasoning_key == "cumin" else "已加辣椒。"


    def finish_bbq_slot(self, slot_index: int) -> tuple[bool, str]:
        """出串按钮入口：把熟烤串写入成品餐库并通知点餐台刷新订单匹配。"""
        slot = self.bbq_slot_state(slot_index)
        if slot is None:
            return False, "这个位置没有烤串。"
        if not self.bbq_slot_cooked(slot_index):
            return False, "烤串还没有烤好。"

        item_key = str(slot.get("key", ""))
        if item_key not in CATALOG:
            return False, "烤串数据异常。"

        cook_seconds = self.bbq_slot_elapsed(slot_index)
        ingredient_keys = [item_key, "cumin"]
        if bool(slot.get("has_chili", False)):
            ingredient_keys.append("chili")
        self.service.record_prepared_dish(
            "bbq",
            ingredient_keys,
            True,
            cook_seconds,
        )
        self.bbq_slots[slot_index] = None
        self.visible_bbq_info_slots.discard(slot_index)
        self.refresh_status()
        self.counter_tab.refresh_orders()
        self.refresh_station_assets()
        return True, f"{CATALOG[item_key].name}已进入餐库。"
