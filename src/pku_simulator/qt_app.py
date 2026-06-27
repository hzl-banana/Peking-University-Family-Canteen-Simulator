"""Qt 应用主装配文件。

这里负责创建 `QApplication`、主窗口、图形场景、页面栈和布局编辑器。具体
业务拆到多个 mixin 中：
- 导航/页面：`qt_app_navigation.py`
- 商店：`qt_shop_controller.py`
- 点餐台状态：`qt_counter_controller.py`
- BGM：`qt_audio.py`
- 图形点击路由：`qt_click_router.py`
- 拖拽投放业务：`qt_workbench_drops.py`
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pku_simulator.core.config import (
    APP_TITLE,
    CANVAS_ASPECT_RATIO,
    PROJECT_ROOT,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from pku_simulator.layout_editor import AssetLayoutStore, SceneLayoutEditor
from pku_simulator.core.save_repo import load_playable_state
from pku_simulator.services.game_service import GameService
from pku_simulator.qt_app_navigation import MainWindowNavigationMixin
from pku_simulator.qt_audio import BackgroundMusicMixin
from pku_simulator.qt_asset_policies import AssetRenderPolicyMixin
from pku_simulator.qt_click_router import GraphicalClickRouterMixin
from pku_simulator.qt_counter_controller import CounterControllerMixin
from pku_simulator.qt_order_taunts import OrderTauntMixin
from pku_simulator.qt_overlays import GraphicalOverlayMixin
from pku_simulator.qt_scene import AspectRatioContainer, BasePage, GameSceneView
from pku_simulator.qt_shop_controller import ShopControllerMixin
from pku_simulator.qt_window_balance import BalanceNotchMixin
from pku_simulator.qt_workbench_drops import WorkbenchDropControllerMixin


class MainWindow(
    OrderTauntMixin,
    GraphicalOverlayMixin,
    AssetRenderPolicyMixin,
    BalanceNotchMixin,
    MainWindowNavigationMixin,
    ShopControllerMixin,
    CounterControllerMixin,
    BackgroundMusicMixin,
    GraphicalClickRouterMixin,
    WorkbenchDropControllerMixin,
    QMainWindow,
):
    """游戏主窗口。

    `GameSceneView` 发出的 Qt signal 会在这里连接到各控制器方法；页面对象
    通过 `main_window` 回调这里完成切屏、刷新场景和调用 `GameService`。
    """

    SCREEN_SCENE_MAP = {
        "start": "start_screen",
        "shop": "shop_screen",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.state = load_playable_state()
        self.service = GameService(self.state)
        self.layout_store = AssetLayoutStore(
            PROJECT_ROOT / "assets" / "asset_positions.json",
            PROJECT_ROOT,
        )
        # 这些 setup 方法来自 mixin，先初始化状态，再创建依赖这些状态的 UI。
        self._ensure_counter_desktop_asset()
        self._setup_background_music()
        self._setup_counter_state()
        self._setup_shop_state()

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._dev_controls_visible = os.environ.get("PKU_SIMULATOR_DEV_CONTROLS") == "1"
        top_bar_widget = QWidget(container)
        top_bar = QHBoxLayout(top_bar_widget)
        top_bar.setContentsMargins(8, 8, 8, 4)
        top_bar.setSpacing(8)

        self.layout_edit_toggle = QCheckBox("布局拖拽模式")
        self.layout_edit_toggle.setChecked(False)
        self.layout_edit_toggle.toggled.connect(self._toggle_layout_editor)

        self.backend_toggle = QCheckBox("后台表格控件")
        self.backend_toggle.setChecked(False)
        self.backend_toggle.toggled.connect(self._toggle_backend_view)

        top_bar.addWidget(self.layout_edit_toggle)
        top_bar.addWidget(self.backend_toggle)
        top_bar.addStretch(1)

        if self._dev_controls_visible:
            root.addWidget(top_bar_widget)

        self.game_scene_view = GameSceneView(
            self.layout_store,
            is_asset_visible=self._asset_visible_for_current_state,
            render_overlay=self._render_graphical_overlay,
            is_bbq_slot_available=self._bbq_slot_available_for_current_state,
        )
        # 图形场景的点击/拖拽信号都汇聚到主窗口控制器，再转发给页面或服务层。
        self.game_scene_view.asset_clicked.connect(self._on_graphical_asset_clicked)
        self.game_scene_view.music_volume_changed.connect(self._set_music_volume)
        self.game_scene_view.cheung_fun_spoon_dropped.connect(
            self._on_cheung_fun_spoon_dropped
        )
        self.game_scene_view.cheung_fun_ingredient_dropped.connect(
            self._on_cheung_fun_ingredient_dropped
        )
        self.game_scene_view.cheung_fun_spatula_dropped.connect(
            self._on_cheung_fun_spatula_dropped
        )
        self.game_scene_view.griddle_ingredient_dropped.connect(
            self._on_griddle_ingredient_dropped
        )
        self.game_scene_view.bbq_skewer_dropped.connect(
            self._on_bbq_skewer_dropped
        )
        self.game_scene_view.bbq_seasoning_dropped.connect(
            self._on_bbq_seasoning_dropped
        )
        self.game_scene_view.staple_ingredient_dropped.connect(
            self._on_staple_ingredient_dropped
        )
        self.stack = QStackedWidget()
        self.game_content_stack = QStackedWidget()
        self.game_content_stack.addWidget(self.game_scene_view)
        self.game_content_stack.addWidget(self.stack)
        self.game_viewport = AspectRatioContainer(self.game_content_stack, CANVAS_ASPECT_RATIO)
        self.layout_editor = SceneLayoutEditor(
            self.layout_store,
            is_asset_visible=self._asset_visible_for_current_state,
            is_asset_rendered=self._asset_rendered_in_layout_editor,
        )
        self.layout_editor.layout_changed.connect(self._on_layout_editor_changed)
        self.layout_editor.setMinimumWidth(420)
        self.layout_editor.setVisible(False)

        self.content_splitter = QSplitter(Qt.Horizontal)
        self.content_splitter.addWidget(self.game_viewport)
        self.content_splitter.addWidget(self.layout_editor)
        self.content_splitter.setStretchFactor(0, 3)
        self.content_splitter.setStretchFactor(1, 2)
        self.content_splitter.setSizes([
            int(WINDOW_WIDTH * 0.66),
            int(WINDOW_WIDTH * 0.34),
        ])

        root.addWidget(self.content_splitter, 1)

        self.setCentralWidget(container)
        self._setup_balance_notch_overlay(container)

        self._order_taunt_text_by_key: dict[tuple[int, str], str] = {}
        self._order_taunt_shown_keys: set[tuple[int, str]] = set()
        self._order_taunt_active_key: tuple[int, str] | None = None
        self._order_taunt_active_text = ""
        self._order_taunt_started_at = 0.0
        self._setup_order_taunt_overlay(container)
        self._order_taunt_timer = QTimer(self)
        self._order_taunt_timer.setInterval(33)
        self._order_taunt_timer.timeout.connect(self.refresh_order_taunt_overlay)
        self._order_taunt_timer.start()

        self._balance_notch_timer = QTimer(self)
        self._balance_notch_timer.setInterval(250)
        self._balance_notch_timer.timeout.connect(self._refresh_balance_notch)
        self._balance_notch_timer.start()

        self._pages: dict[str, BasePage] = {}
        self._current_name = ""
        self._build_pages()
        self.change_screen("start")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._position_balance_notch_overlay()
        self._position_order_taunt_overlay()

class QtApp:
    """轻量 Qt 应用包装；入口脚本只需要创建它并调用 `run()`。"""

    def __init__(self) -> None:
        self._qapp = QApplication.instance() or QApplication(sys.argv)
        self._qapp.setApplicationName(APP_TITLE)
        self.window = MainWindow()

    def run(self) -> None:
        self.window.show()
        self._qapp.exec()
