"""图形点击路由。

`GameSceneView.asset_clicked` 会把图形项的 data 字符串发到这里。本模块根据
字符串前缀把点击分发到商店、点餐台、工作台信息框、底部导航或音乐设置。
"""

from __future__ import annotations

from pku_simulator.qt_pages import ShopPage, WorkbenchPage


class GraphicalClickRouterMixin:
    """点击 data -> 控制器方法的分发表。

    所有可点击覆盖层都应设置稳定的 data 前缀，例如 `buy:key:qty`、
    `dock:scene_key`、`counter_ticket:id`。
    """

    def _on_graphical_asset_clicked(self, asset_name: str) -> None:
        """主点击入口；由 `qt_app.MainWindow` 连接到 `GameSceneView.asset_clicked`。"""
        if self._current_name == "start" and asset_name == "开局按钮.jpg":
            self.open_start_shop()
        elif asset_name == "music_settings:toggle":
            self._music_settings_visible = not self._music_settings_visible
            self.game_scene_view.refresh_overlay()
        elif asset_name == "music_settings:close":
            self._music_settings_visible = False
            self.game_scene_view.refresh_overlay()
        elif asset_name.startswith("music_volume_delta:"):
            try:
                delta = float(asset_name.removeprefix("music_volume_delta:"))
            except ValueError:
                return
            self._set_music_volume(self._music_volume + delta)
        elif asset_name == "music_settings:panel":
            return
        elif self._current_name == "workbench" and asset_name == "counter_overlay_close":
            if self._counter_zoomed_order_id is not None:
                self._counter_zoomed_order_id = None
                self.game_scene_view.refresh_overlay()
                return
        elif self._current_name == "workbench" and asset_name.startswith("counter_customer:"):
            self._on_counter_customer_clicked(asset_name)
            return
        elif self._current_name == "workbench" and asset_name.startswith("counter_accept:"):
            self._on_counter_accept_clicked(asset_name)
            return
        elif self._current_name == "workbench" and asset_name.startswith("counter_order_done:"):
            self._on_counter_order_done_clicked(asset_name)
            return
        elif self._current_name == "workbench" and asset_name.startswith("counter_ticket:"):
            self._on_counter_ticket_clicked(asset_name)
            return
        elif self._current_name == "workbench" and asset_name.startswith("counter_serve:"):
            self._on_counter_serve_clicked(asset_name)
            return
        elif self._current_name == "workbench" and asset_name.startswith("dock:"):
            scene_key = asset_name.removeprefix("dock:")
            if scene_key == "shop":
                self.open_workbench_shop()
                return
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage) and workbench.switch_to_scene(scene_key):
                self.game_scene_view.set_scene_key(scene_key)
                self.layout_editor.set_scene_key(scene_key)
        elif self._current_name == "workbench" and asset_name.startswith("griddle_pan:"):
            try:
                pan_index = int(asset_name.removeprefix("griddle_pan:"))
            except ValueError:
                return
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage):
                success, message = workbench.toggle_griddle_info_panel(pan_index)
                if message:
                    workbench.notify_message(message, success=success)
                self.game_scene_view.refresh_overlay()
        elif self._current_name == "workbench" and asset_name.startswith("griddle_out:"):
            try:
                pan_index = int(asset_name.removeprefix("griddle_out:"))
            except ValueError:
                return
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage):
                success, message = workbench.finish_griddle_pan(pan_index)
                workbench.notify_message(message, success=success)
                self.game_scene_view.refresh_overlay()
        elif self._current_name == "workbench" and asset_name.startswith("cheung_fun_pan:"):
            try:
                pan_index = int(asset_name.removeprefix("cheung_fun_pan:"))
            except ValueError:
                return
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage):
                success, message = workbench.toggle_cheung_fun_info_panel(pan_index)
                if message:
                    workbench.notify_message(message, success=success)
                self.game_scene_view.refresh_overlay()
        elif self._current_name == "workbench" and asset_name.startswith("cheung_fun_out:"):
            try:
                pan_index = int(asset_name.removeprefix("cheung_fun_out:"))
            except ValueError:
                return
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage):
                success, message = workbench.finish_cheung_fun_pan(pan_index)
                workbench.notify_message(message, success=success)
                self.game_scene_view.refresh_overlay()
        elif self._current_name == "workbench" and asset_name.startswith("bbq_slot:"):
            try:
                slot_index = int(asset_name.removeprefix("bbq_slot:"))
            except ValueError:
                return
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage):
                success, message = workbench.toggle_bbq_info_slot(slot_index)
                if message:
                    workbench.notify_message(message, success=success)
                self.game_scene_view.refresh_overlay()
        elif self._current_name == "workbench" and asset_name.startswith("bbq_finish:"):
            try:
                slot_index = int(asset_name.removeprefix("bbq_finish:"))
            except ValueError:
                return
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage):
                success, message = workbench.finish_bbq_slot(slot_index)
                workbench.notify_message(message, success=success)
                self.game_scene_view.refresh_overlay()
        elif self._current_name == "workbench" and asset_name.startswith("staple_cooker:"):
            try:
                cooker_index = int(asset_name.removeprefix("staple_cooker:"))
            except ValueError:
                return
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage):
                success, message = workbench.toggle_staple_info_panel(cooker_index)
                if message:
                    workbench.notify_message(message, success=success)
                self.game_scene_view.refresh_overlay()
        elif self._current_name == "workbench" and asset_name.startswith("staple_start:"):
            try:
                cooker_index = int(asset_name.removeprefix("staple_start:"))
            except ValueError:
                return
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage):
                success, message = workbench.start_staple_cooker(cooker_index)
                if message:
                    workbench.notify_message(message, success=success)
                self.game_scene_view.refresh_overlay()
        elif self._current_name == "workbench" and asset_name.startswith("staple_finish:"):
            try:
                cooker_index = int(asset_name.removeprefix("staple_finish:"))
            except ValueError:
                return
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage):
                success, message = workbench.finish_staple_cooker(cooker_index)
                if message:
                    workbench.notify_message(message, success=success)
                self.game_scene_view.refresh_overlay()
        elif self._current_name == "shop" and asset_name.startswith("buy:"):
            parts = asset_name.split(":")
            item_key = parts[1] if len(parts) > 1 else ""
            try:
                quantity = int(parts[2]) if len(parts) > 2 else 1
            except ValueError:
                quantity = 1
            success, message = self.buy_shop_ingredient(item_key, quantity=quantity)
            page = self._pages.get("shop")
            if isinstance(page, ShopPage):
                page._set_message(message, success)
                page._refresh()
            self.game_scene_view.refresh_overlay()
        elif self._current_name == "shop" and asset_name in {"shop_finish", "完成采购红色背景按钮.jpg"}:
            page = self._pages.get("shop")
            if isinstance(page, ShopPage):
                page._confirm()
