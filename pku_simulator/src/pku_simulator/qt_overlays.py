"""图形 overlay 的总调度入口。

`MainWindow.refresh_station_assets()` 会在场景重绘后调用这里，根据当前
`scene_key` 分发到 start/shop/workbench/counter 各个 overlay mixin。
"""

from __future__ import annotations

from pku_simulator.qt_pages import WorkbenchPage
from pku_simulator.qt_scene import GameSceneView
from pku_simulator.qt_overlays_counter import CounterOverlayMixin
from pku_simulator.qt_overlays_start_shop import StartShopOverlayMixin
from pku_simulator.qt_overlays_workbench import WorkbenchOverlayMixin


class GraphicalOverlayMixin(
    StartShopOverlayMixin,
    WorkbenchOverlayMixin,
    CounterOverlayMixin,
):
    """把多个场景 overlay mixin 汇总成主窗口可调用的统一接口。"""

    def _render_graphical_overlay(self, view: GameSceneView, scene_key: str) -> None:
        """按场景绘制额外 UI，并在最后叠加工作台 dock 与音乐设置按钮。"""
        if scene_key == "start_screen":
            self._render_start_overlay(view)
        elif scene_key == "shop_screen":
            self._render_shop_overlay(view)
        elif scene_key == "griddle_station":
            self._render_griddle_overlay(view)
        elif scene_key == "cheung_fun_station":
            self._render_cheung_fun_overlay(view)
        elif scene_key == "staple_station":
            self._render_staple_overlay(view)
        elif scene_key == "bbq_station":
            self._render_bbq_overlay(view)
        elif scene_key == "counter_station":
            self._render_counter_overlay(view)

        if scene_key in WorkbenchPage.TAB_SCENE_KEYS:
            self._render_workbench_dock(view, scene_key)
        self._render_music_settings_overlay(view)


__all__ = ["GraphicalOverlayMixin"]
