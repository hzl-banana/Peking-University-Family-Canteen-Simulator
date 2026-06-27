"""图形场景视图和基础页面容器。

`GameSceneView` 根据 `asset_positions.json` 加载静态素材，再调用
`GraphicalOverlayMixin` 绘制运行时覆盖层。鼠标拖拽逻辑在
`qt_scene_drag.py`，绘制辅助在 `qt_scene_drawing.py`。
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)

from pku_simulator.core.config import CANVAS_HEIGHT, CANVAS_WIDTH
from pku_simulator.layout_editor import AssetLayoutStore
from pku_simulator.qt_defs import *
from pku_simulator.qt_scene_drag import SceneDragMixin
from pku_simulator.qt_scene_drawing import SceneDrawingMixin


class BasePage(QWidget):
    """所有后台 QWidget 页面基类。

    子类通过 `self.main_window` 访问主窗口，通过 `state/service` 只读属性访问
    当前游戏状态和业务服务。
    """

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self.main_window = main_window

    @property
    def state(self):
        return self.main_window.state

    @property
    def service(self):
        return self.main_window.service

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass


class AspectRatioContainer(QWidget):
    """把内部游戏内容固定在设计画布比例内，窗口多余部分留黑边。"""

    def __init__(self, content: QWidget, aspect_ratio: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._content = content
        self._aspect_ratio = aspect_ratio
        self._content.setParent(self)
        self._content.setAutoFillBackground(True)
        self._content.setStyleSheet("background-color: #f8fafc;")
        self.setMinimumSize(320, 200)
        self.setStyleSheet("background-color: #000000;")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        available_w = max(1, self.width())
        available_h = max(1, self.height())

        if available_w / available_h > self._aspect_ratio:
            target_h = available_h
            target_w = int(round(target_h * self._aspect_ratio))
        else:
            target_w = available_w
            target_h = int(round(target_w / self._aspect_ratio))

        x = (available_w - target_w) // 2
        y = (available_h - target_h) // 2
        self._content.setGeometry(x, y, target_w, target_h)


class GameSceneView(SceneDragMixin, SceneDrawingMixin, QGraphicsView):
    """主图形场景。

    对外 signal：
    - `asset_clicked(str)`：普通点击，交给 `qt_click_router.py`。
    - `*_dropped(...)`：拖拽命中，交给 `qt_workbench_drops.py`。
    - `music_volume_changed(float)`：音乐面板滑块，交给 `qt_audio.py`。
    """

    asset_clicked = Signal(str)
    griddle_ingredient_dropped = Signal(str, int)
    cheung_fun_spoon_dropped = Signal(str, int)
    cheung_fun_ingredient_dropped = Signal(str, int)
    cheung_fun_spatula_dropped = Signal(int)
    bbq_skewer_dropped = Signal(str, int)
    bbq_seasoning_dropped = Signal(str, int)
    staple_ingredient_dropped = Signal(str, int)
    music_volume_changed = Signal(float)

    def __init__(
        self,
        store: AssetLayoutStore,
        is_asset_visible: Callable[[str], bool],
        render_overlay: Callable[["GameSceneView", str], None] | None = None,
        is_bbq_slot_available: Callable[[int], bool] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.graphics_scene = QGraphicsScene(self)
        self.setScene(self.graphics_scene)
        self.store = store
        self._is_asset_visible = is_asset_visible
        self._render_overlay = render_overlay
        self._is_bbq_slot_available = is_bbq_slot_available
        self._scene_key = ""
        self._drag_item: QGraphicsPixmapItem | None = None
        self._drag_item_start = QPointF()
        self._drag_press_scene_pos = QPointF()
        self._drag_offset = QPointF()
        self._drag_item_z = 0.0
        self._drag_payload = ""
        self._drag_moved = False
        self._music_volume_drag_item = None
        self._last_griddle_drop_item: QGraphicsPixmapItem | None = None
        self._garbage_fade_timers: list[QTimer] = []
        self._return_timers: list[QTimer] = []
        self._bbq_seasoning_timers: list[QTimer] = []
        self._reload_pending = False
        self._pixmap_cache: dict[tuple[str, int, int, int], QPixmap] = {}
        self._overlay_items = []
        self._rendering_overlay = False
        self._garbage_asset_name = "烤盘间的垃圾桶.png"

        self.setAlignment(Qt.AlignCenter)
        self.setBackgroundBrush(Qt.black)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(
            "QGraphicsView { background-color: #000000; }"
            "QScrollBar:vertical {"
            " background: rgba(255, 255, 255, 40);"
            " width: 14px;"
            " margin: 8px 6px 8px 6px;"
            " border-radius: 7px;"
            "}"
            "QScrollBar::handle:vertical {"
            " background: rgba(127, 29, 29, 150);"
            " min-height: 48px;"
            " border-radius: 7px;"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            " height: 0px;"
            "}"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {"
            " background: transparent;"
            "}"
        )

    def set_scene_key(self, scene_key: str) -> None:
        """切换到 `asset_positions.json` 中的某个 scene，并重载资源。"""
        scene_key = scene_key.strip()
        if not scene_key:
            return
        self._scene_key = scene_key
        self.reload_scene()

    def scene_key(self) -> str:
        """返回当前 scene key，主窗口和覆盖层同步时会读取它。"""
        return self._scene_key

    def is_dragging(self) -> bool:
        """拖拽中不立即重载场景，避免拖动的图形项被清掉。"""
        return self._drag_item is not None

    def reload_scene(self) -> None:
        """加载当前 scene 的静态素材，并在最后调用覆盖层渲染。"""
        if self.is_dragging() or self._return_timers:
            self._reload_pending = True
            return

        previous_scroll_value = (
            self.verticalScrollBar().value()
            if self._scene_key == "shop_screen"
            else 0
        )
        self._reload_pending = False
        self.graphics_scene.clear()
        self._overlay_items.clear()
        if not self._scene_key:
            return

        names = [
            name
            for name in self.store.scene_asset_names(self._scene_key, include_shared=True)
            if self._is_asset_visible(name)
        ]

        width = 1
        height = 1
        for name in names:
            # 动态素材由 overlay/mixin 在运行时绘制，静态层只画背景和可拖源。
            if name == MUSIC_GEAR_ASSET_NAME:
                continue
            if self._scene_key == "start_screen" and name == "开局按钮.jpg":
                continue
            if self._scene_key == "shop_screen":
                continue
            if self._scene_key == "griddle_station" and name in GRIDDLE_DYNAMIC_ASSET_NAMES:
                continue
            if self._scene_key == "cheung_fun_station":
                asset = self.store.asset_metadata(name)
                if (
                    name in CHEUNG_FUN_DYNAMIC_ASSET_NAMES
                    or name in CHEUNG_FUN_SUPPRESSED_STATIC_ASSET_NAMES
                    or asset.get("category") == "labels"
                    or "标签" in name
                ):
                    continue
            if self._scene_key == "bbq_station" and name in BBQ_SUPPRESSED_STATIC_ASSET_NAMES:
                continue
            if self._scene_key == "staple_station":
                asset = self.store.asset_metadata(name)
                if (
                    name in STAPLE_DYNAMIC_ASSET_NAMES
                    or asset.get("category") == "labels"
                    or "标签" in name
                ):
                    continue
            if self._scene_key == "counter_station" and name not in {"点餐台背景.jpg"}:
                continue

            x, y, w, h, layer = self.store.asset_geometry(name)
            item = QGraphicsPixmapItem(self._load_scaled_pixmap(name, w, h))
            self._apply_asset_visual_transform(item, name, w, h)
            item.setPos(float(x), float(y))
            item.setZValue(float(layer))
            item_data = name
            if self._scene_key == "griddle_station":
                if name in GRIDDLE_KEYS_BY_ASSET_NAME:
                    item_data = f"griddle_ingredient:{GRIDDLE_KEYS_BY_ASSET_NAME[name]}:{name}"
                    item.setCursor(Qt.OpenHandCursor)
                elif name in GRIDDLE_PAN_ASSET_NAMES:
                    item_data = f"griddle_pan:{GRIDDLE_PAN_ASSET_NAMES.index(name)}"
                    item.setCursor(Qt.PointingHandCursor)
            elif self._scene_key == "cheung_fun_station":
                if name in CHEUNG_FUN_INGREDIENT_ASSET_KEYS:
                    item_data = f"cheung_fun_ingredient:{CHEUNG_FUN_INGREDIENT_ASSET_KEYS[name]}:{name}"
                    item.setCursor(Qt.OpenHandCursor)
                elif name == CHEUNG_FUN_SPATULA_ASSET_NAME:
                    item_data = "cheung_fun_spatula"
                    item.setCursor(Qt.OpenHandCursor)
            elif self._scene_key == "bbq_station":
                seasoning_key = BBQ_SEASONING_ASSET_KEYS.get(name)
                if seasoning_key is not None:
                    item_data = f"bbq_seasoning:{seasoning_key}:{name}"
                    item.setCursor(Qt.OpenHandCursor)
                else:
                    skewer_key = BBQ_SKEWER_KEYS_BY_ASSET_NAME.get(name)
                    if skewer_key is not None:
                        item_data = f"bbq_skewer_source:{skewer_key}:{name}"
                        item.setCursor(Qt.OpenHandCursor)
            elif self._scene_key == "staple_station":
                source_key = STAPLE_SOURCE_ASSET_KEYS.get(name)
                if source_key is not None:
                    item_data = f"staple_ingredient:{source_key}:{name}"
                    item.setCursor(Qt.OpenHandCursor)
            item.setData(0, item_data)
            self.graphics_scene.addItem(item)
            width = max(width, x + w)
            height = max(height, y + h)

        if self._scene_key == "shop_screen":
            width = max(width, CANVAS_WIDTH)
            height = max(height, SHOP_SCENE_HEIGHT)
        elif self._scene_key in {
            "griddle_station",
            "cheung_fun_station",
            "staple_station",
            "bbq_station",
            "counter_station",
        }:
            width = max(width, CANVAS_WIDTH)
            height = max(height, CANVAS_HEIGHT)

        self.graphics_scene.setSceneRect(0, 0, width, height)
        self._fit_current_scene()
        if self._scene_key == "shop_screen":
            self.verticalScrollBar().setValue(
                min(previous_scroll_value, self.verticalScrollBar().maximum())
            )
            if previous_scroll_value <= 0:
                self.verticalScrollBar().setValue(0)
        self.refresh_overlay()

    def refresh_overlay(self) -> None:
        """清掉上一帧覆盖层并让主窗口重新绘制运行时 UI。"""
        if not self._scene_key or self._render_overlay is None:
            return

        drag_item = self._drag_item
        for item in self._overlay_items:
            if drag_item is not None and item is drag_item:
                continue
            if item.scene() is self.graphics_scene:
                self.graphics_scene.removeItem(item)
        self._overlay_items = [
            item
            for item in self._overlay_items
            if drag_item is not None and item is drag_item
        ]

        self._rendering_overlay = True
        try:
            self._render_overlay(self, self._scene_key)
        finally:
            self._rendering_overlay = False

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if not self.graphics_scene.sceneRect().isEmpty():
            self._fit_current_scene()
            self.refresh_overlay()

    def scrollContentsBy(self, dx: int, dy: int) -> None:  # type: ignore[override]
        super().scrollContentsBy(dx, dy)
        if self._scene_key == "shop_screen" and self._render_overlay is not None:
            self.refresh_overlay()

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        if self._scene_key == "shop_screen":
            delta = event.pixelDelta().y()
            if delta == 0:
                delta = event.angleDelta().y()
            if delta != 0:
                bar = self.verticalScrollBar()
                bar.setValue(bar.value() - int(delta))
                event.accept()
                return
        super().wheelEvent(event)
