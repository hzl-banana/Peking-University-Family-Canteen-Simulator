"""工作台拖拽投放后的业务处理。

`GameSceneView` 只负责命中检测和发 signal；食材库存扣减、工作台状态更新、
提示文字和场景刷新都在这里完成。
"""

from __future__ import annotations

from pku_simulator.core.catalog import CATALOG
from pku_simulator.qt_pages import WorkbenchPage


class WorkbenchDropControllerMixin:
    """`GameSceneView` 拖拽 signal -> `WorkbenchPage` 业务方法的适配层。"""

    def _bbq_slot_available_for_current_state(self, slot_index: int) -> bool:
        """供场景视图吸附烤串时判断烧烤槽位是否可用。"""
        if self._current_name != "workbench":
            return True
        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            return True
        return workbench.bbq_slot_state(slot_index) is None

    def _on_griddle_ingredient_dropped(self, item_key: str, pan_index: int) -> None:
        """烤盘食材投放：先扣库存，再写入对应锅或垃圾桶。"""
        if self._current_name != "workbench" or item_key not in CATALOG:
            self.game_scene_view.reload_scene()
            return

        success, message = self.service.consume_ingredient(item_key, 1)
        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            self.game_scene_view.reload_scene()
            return

        if not success:
            workbench.notify_message(message, success=False)
            self.game_scene_view.reload_scene()
            return

        if pan_index >= 0:
            added, add_message = workbench.add_griddle_ingredient_to_pan(pan_index, item_key)
            workbench.notify_message(add_message, success=added)
            workbench.refresh_status()
            if added:
                self.game_scene_view.reload_scene()
            else:
                self.game_scene_view.flash_last_griddle_drop_to_garbage()
        else:
            workbench.notify_message(f"{CATALOG[item_key].name} 已丢入垃圾桶", success=False)
            workbench.refresh_status()

    def _on_cheung_fun_spoon_dropped(self, action: str, pan_index: int) -> None:
        """肠粉勺子投放：`fill` 表示取面糊，`pour` 表示倒入某个烤台。"""
        if self._current_name != "workbench":
            self.game_scene_view.reload_scene()
            return

        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            self.game_scene_view.reload_scene()
            return

        if action == "fill":
            success, message = workbench.fill_cheung_fun_spoon()
        elif action == "pour":
            success, message = workbench.pour_cheung_fun_batter_to_pan(pan_index)
        else:
            return

        if message:
            workbench.notify_message(message, success=success)

    def _on_cheung_fun_ingredient_dropped(self, item_key: str, pan_index: int) -> None:
        """肠粉配料投放：鸡蛋/鲜虾入锅，鲜虾也支持丢进垃圾桶。"""
        if self._current_name != "workbench":
            self.game_scene_view.reload_scene()
            return

        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            self.game_scene_view.reload_scene()
            return

        if pan_index < 0:
            if item_key == "shrimp":
                success, message = self.service.consume_ingredient(item_key, 1)
                if success:
                    workbench.notify_message("鲜虾已丢入垃圾桶", success=False)
                else:
                    workbench.notify_message(message, success=False)
                    self.game_scene_view.reload_scene()
                workbench.refresh_status()
                return

            self.game_scene_view.reload_scene()
            return

        success, message = workbench.add_cheung_fun_ingredient_to_pan(pan_index, item_key)
        if message:
            workbench.notify_message(message, success=success)
        self.game_scene_view.reload_scene()

    def _on_cheung_fun_spatula_dropped(self, pan_index: int) -> None:
        """肠粉铲勺投放：对指定烤台执行搅拌/出锅前处理。"""
        if self._current_name != "workbench":
            self.game_scene_view.reload_scene()
            return

        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            self.game_scene_view.reload_scene()
            return

        success, message = workbench.stir_cheung_fun_pan(pan_index)
        if message:
            workbench.notify_message(message, success=success)
        self.game_scene_view.reload_scene()

    def _on_bbq_skewer_dropped(self, item_key: str, slot_index: int) -> None:
        """烧烤原串投放：写入指定烤架槽位。"""
        if self._current_name != "workbench":
            self.game_scene_view.reload_scene()
            return

        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            self.game_scene_view.reload_scene()
            return

        success, message = workbench.add_bbq_skewer_to_slot(slot_index, item_key)
        if message:
            workbench.notify_message(message, success=success)
        self.game_scene_view.reload_scene()

    def _on_bbq_seasoning_dropped(self, seasoning_key: str, slot_index: int) -> None:
        """烧烤调料投放：给已有烤串批量加孜然/辣椒。"""
        if self._current_name != "workbench":
            self.game_scene_view.reload_scene()
            return

        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            self.game_scene_view.reload_scene()
            return

        success, message = workbench.season_bbq_slot(slot_index, seasoning_key)
        if message:
            workbench.notify_message(message, success=success)
        self.game_scene_view.refresh_overlay()

    def _on_staple_ingredient_dropped(self, item_key: str, cooker_index: int) -> None:
        """主食区米/水投放：写入指定电饭煲状态。"""
        if self._current_name != "workbench":
            self.game_scene_view.reload_scene()
            return

        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            self.game_scene_view.reload_scene()
            return

        success, message = workbench.add_staple_ingredient_to_cooker(cooker_index, item_key)
        if message:
            workbench.notify_message(message, success=success)
        self.game_scene_view.reload_scene()
