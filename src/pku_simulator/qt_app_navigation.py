"""主窗口导航和页面同步。

这个 mixin 被 `MainWindow` 继承：负责构建页面栈、切屏、同步当前图形场景、
处理布局编辑器刷新，以及重开新局。
"""

from __future__ import annotations

from pku_simulator.core.config import CANVAS_HEIGHT, CANVAS_WIDTH
from pku_simulator.core.models import GameState
from pku_simulator.core.save_repo import save_state
from pku_simulator.qt_defs import COUNTER_DESK_ASSET_NAME
from pku_simulator.qt_pages import GameOverPage, ShopPage, StartPage, WorkbenchPage
from pku_simulator.services.game_service import GameService


class MainWindowNavigationMixin:
    """页面/场景导航接口。

    依赖 `MainWindow` 提供的属性：`stack`、`game_scene_view`、`layout_editor`、
    `state`、`service`、`_pages` 和 `_current_name`。
    """

    def _build_pages(self) -> None:
        """创建开始、商店、营业区和失败页，并接上营业区场景切换信号。"""
        while self.stack.count() > 0:
            old_widget = self.stack.widget(0)
            self.stack.removeWidget(old_widget)
            old_widget.deleteLater()

        self._pages = {
            "start": StartPage(self),
            "shop": ShopPage(self),
            "workbench": WorkbenchPage(self),
            "game_over": GameOverPage(self),
        }

        workbench = self._pages.get("workbench")
        if isinstance(workbench, WorkbenchPage):
            workbench.scene_changed.connect(self._on_workbench_scene_changed)

        for page in self._pages.values():
            self.stack.addWidget(page)

    def _ensure_counter_desktop_asset(self) -> None:
        """确保点餐台前景桌面素材存在；老位置文件缺这个条目时自动补上。"""
        if self.layout_store.asset_metadata(COUNTER_DESK_ASSET_NAME):
            return

        self.layout_store._assets[COUNTER_DESK_ASSET_NAME] = {
            "path": "assets/placeholders/功能性图片/点餐台桌面.png",
            "category": "functional",
            "scene": "counter_station",
            "position": {
                "x": 0,
                "y": 0,
                "width": CANVAS_WIDTH,
                "height": CANVAS_HEIGHT,
                "anchor": "top-left",
                "layer": 120,
            },
            "visible": True,
            "note": "点餐台前景桌面；用于遮挡顾客下半身。",
            "order": 24,
        }
        self.layout_store.save()

    def change_screen(self, name: str) -> None:
        """统一切屏入口；页面生命周期、场景、BGM 和浮层都在这里同步。"""
        if name not in self._pages:
            raise KeyError(f"Unknown page: {name}")

        if self._current_name:
            self._pages[self._current_name].on_exit()

        self._current_name = name
        page = self._pages[name]
        self.stack.setCurrentWidget(page)
        page.on_enter()
        self._sync_content_stack()
        self._sync_layout_scene()
        self._reset_game_scene_scroll()
        self._sync_background_music()
        self._refresh_balance_notch()
        self.refresh_order_taunt_overlay()

    def _toggle_layout_editor(self, enabled: bool) -> None:
        """开发控件：显示/隐藏右侧布局编辑器。"""
        self.layout_editor.setVisible(enabled)
        if enabled:
            self._sync_layout_scene()

    def _toggle_backend_view(self, enabled: bool) -> None:
        """开发控件：在图形场景和后台表格页面之间切换。"""
        self._sync_content_stack()
        self._sync_layout_scene()

    def _reset_game_scene_scroll(self) -> None:
        """切屏后把图形视图滚动条复位，避免商店滚动位置影响其它场景。"""
        bar = self.game_scene_view.verticalScrollBar()
        if bar is not None:
            bar.setValue(0)

    def _sync_content_stack(self) -> None:
        """决定当前显示图形场景还是后台 QWidget 页面。"""
        use_backend = self.backend_toggle.isChecked() or self._current_name == "game_over"
        self.game_content_stack.setCurrentWidget(self.stack if use_backend else self.game_scene_view)

    def _current_scene_key(self) -> str:
        """把页面名映射到 `asset_positions.json` 中的 scene key。"""
        if self._current_name == "workbench":
            workbench = self._pages.get("workbench")
            if isinstance(workbench, WorkbenchPage):
                return workbench.current_scene_key()
            return "griddle_station"
        return self.SCREEN_SCENE_MAP.get(self._current_name, "start_screen")

    def _sync_layout_scene(self) -> None:
        """让主图形场景和布局编辑器使用同一个 scene key。"""
        scene_key = self._current_scene_key()
        self.game_scene_view.set_scene_key(scene_key)
        self.layout_editor.set_scene_key(scene_key)

    def _on_layout_editor_changed(self) -> None:
        """布局编辑器写回坐标后刷新主图形场景。"""
        self.game_scene_view.reload_scene()

    def _on_workbench_scene_changed(self, scene_key: str) -> None:
        """营业区底部导航/后台标签切换后同步图形场景。"""
        if self._current_name == "workbench":
            if scene_key == "counter_station":
                self.sync_counter_orders()
            if (
                scene_key in {"griddle_station", "staple_station", "bbq_station"}
                and self.game_scene_view.scene_key() == scene_key
            ):
                self.game_scene_view.refresh_overlay()
            else:
                self.game_scene_view.set_scene_key(scene_key)
            self.layout_editor.set_scene_key(scene_key)
            self._sync_background_music()

    def reset_game(self) -> None:
        """失败页重开入口；重置状态、保存并回到开始页。"""
        self.state = GameState()
        self.service = GameService(self.state)
        save_state(self.state)
        self._build_pages()
        self.change_screen("start")
