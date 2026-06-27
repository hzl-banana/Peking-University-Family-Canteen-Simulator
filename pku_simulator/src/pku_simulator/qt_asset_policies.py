"""素材显示策略。

`GameSceneView` 在加载场景资源时会调用 `_asset_visible_for_current_state()`，
布局编辑器则调用 `_asset_rendered_in_layout_editor()`。这里把“库存是否足够、
设备是否损坏、哪些动态素材应隐藏”等规则集中起来。
"""

from __future__ import annotations

from pku_simulator.qt_defs import *
from pku_simulator.qt_pages import WorkbenchPage


class AssetRenderPolicyMixin:
    """主窗口素材可见性接口；依赖 `layout_store`、`service` 和 `WorkbenchPage`。"""

    def _asset_visible_for_current_state(self, asset_name: str) -> bool:
        """运行中场景使用：决定某个素材此刻是否应绘制。"""
        asset = self.layout_store.asset_metadata(asset_name)
        if not bool(asset.get("visible", True)):
            return False

        inventory_key = asset.get("inventory_key")
        if isinstance(inventory_key, str) and inventory_key:
            min_quantity = _safe_int(asset.get("min_quantity"), 1)
            return self.service.get_quantity(inventory_key) >= max(1, min_quantity)

        cheung_fun_inventory_key = CHEUNG_FUN_KEY_BY_INVENTORY_ASSET_NAME.get(asset_name)
        if cheung_fun_inventory_key is not None:
            return self.service.get_quantity(cheung_fun_inventory_key) > 0

        if asset_name in GRIDDLE_PAN_ASSET_NAMES:
            pan_index = GRIDDLE_PAN_ASSET_NAMES.index(asset_name)
            workbench = self._pages.get("workbench")
            if (
                isinstance(workbench, WorkbenchPage)
                and 0 <= pan_index < len(workbench.griddle_pans)
            ):
                return not bool(workbench.griddle_pans[pan_index].get("broken", False))

        griddle_key = GRIDDLE_KEYS_BY_ASSET_NAME.get(asset_name)
        if griddle_key is not None:
            return self.service.get_quantity(griddle_key) > 0

        staple_key = STAPLE_SOURCE_ASSET_KEYS.get(asset_name)
        if staple_key is not None:
            return self.service.get_quantity(staple_key) > 0

        bbq_skewer_key = BBQ_SKEWER_KEYS_BY_ASSET_NAME.get(asset_name)
        if bbq_skewer_key is not None:
            return self.service.get_quantity(bbq_skewer_key) > 0

        bbq_seasoning_key = BBQ_SEASONING_ASSET_KEYS.get(asset_name)
        if bbq_seasoning_key is not None:
            return self.service.get_quantity(bbq_seasoning_key) > 0

        return True

    def _asset_rendered_in_layout_editor(self, asset_name: str, scene_key: str) -> bool:
        """布局编辑器使用：隐藏运行时动态素材，只保留可调坐标的对象。"""
        asset = self.layout_store.asset_metadata(asset_name)
        if not bool(asset.get("visible", True)):
            return False

        if scene_key == "cheung_fun_station":
            return not (
                asset_name in CHEUNG_FUN_SUPPRESSED_STATIC_ASSET_NAMES
                or asset_name == CHEUNG_FUN_FILLED_SPOON_ASSET_NAME
                or asset.get("category") == "labels"
                or "标签" in asset_name
            )

        if scene_key == "bbq_station":
            return asset_name not in BBQ_LAYOUT_EDITOR_SUPPRESSED_ASSET_NAMES

        if scene_key == "staple_station":
            return not (
                asset_name in {
                    "主食区背景.jpg",
                    "电饭煲.jpg",
                    "爆炸的电饭煲.jpg",
                }
                or asset.get("category") == "labels"
                or "标签" in asset_name
            )
        if scene_key == "counter_station":
            return asset_name in {"点餐台背景.jpg", COUNTER_DESK_ASSET_NAME}

        return True
