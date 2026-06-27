"""`GameSceneView` 的鼠标拖拽和命中逻辑。

本模块只决定“拖到哪里”和“发什么 signal”。真正扣库存、修改工作台状态的
业务在 `qt_workbench_drops.py`，避免图形视图直接碰业务数据。
"""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsPixmapItem

from pku_simulator.qt_defs import *


class SceneDragMixin:
    """拖拽交互接口；依赖 `GameSceneView` 的 scene、store 和 Qt signals。"""

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """按下时识别可拖素材、覆盖层按钮或音量滑块。"""
        scene_pos = self.mapToScene(event.pos())
        items = self.graphics_scene.items(scene_pos)
        for item in items:
            asset_name = item.data(0)
            if asset_name == "music_volume_slider":
                self._music_volume_drag_item = item
                self._emit_music_volume_from_slider(item, scene_pos)
                event.accept()
                return

        for item in items:
            asset_name = item.data(0)
            if isinstance(asset_name, str) and (
                asset_name.startswith("griddle_out:")
                or asset_name.startswith("cheung_fun_out:")
            ):
                self.asset_clicked.emit(asset_name)
                event.accept()
                return

        for clicked_item in items:
            asset_name = clicked_item.data(0)
            if isinstance(asset_name, str):
                if "背景" in asset_name:
                    continue
                if asset_name.startswith("griddle_ingredient:"):
                    self._drag_item = clicked_item if isinstance(clicked_item, QGraphicsPixmapItem) else None
                    if self._drag_item is not None:
                        self._drag_item_start = self._drag_item.pos()
                        self._drag_press_scene_pos = scene_pos
                        self._drag_offset = scene_pos - self._drag_item.pos()
                        self._drag_item_z = self._drag_item.zValue()
                        self._drag_payload = asset_name
                        self._drag_moved = False
                        self._drag_item.setZValue(1000)
                        self._drag_item.setOpacity(0.72)
                        self._drag_item.setCursor(Qt.ClosedHandCursor)
                        self.viewport().grabMouse()
                        event.accept()
                        return
                if asset_name.startswith("cheung_fun_spoon:"):
                    self._drag_item = clicked_item if isinstance(clicked_item, QGraphicsPixmapItem) else None
                    if self._drag_item is not None:
                        self._drag_item_start = self._drag_item.pos()
                        self._drag_press_scene_pos = scene_pos
                        self._drag_offset = scene_pos - self._drag_item.pos()
                        self._drag_item_z = self._drag_item.zValue()
                        self._drag_payload = asset_name
                        self._drag_moved = False
                        self._drag_item.setZValue(1000)
                        self._drag_item.setOpacity(0.82)
                        self._drag_item.setCursor(Qt.ClosedHandCursor)
                        self.viewport().grabMouse()
                        event.accept()
                        return
                if (
                    asset_name.startswith("cheung_fun_ingredient:")
                    or asset_name == "cheung_fun_spatula"
                    or asset_name.startswith("bbq_seasoning:")
                    or asset_name.startswith("bbq_skewer_source:")
                    or asset_name.startswith("staple_ingredient:")
                ):
                    self._drag_item = clicked_item if isinstance(clicked_item, QGraphicsPixmapItem) else None
                    if self._drag_item is not None:
                        self._drag_item_start = self._drag_item.pos()
                        self._drag_press_scene_pos = scene_pos
                        self._drag_offset = scene_pos - self._drag_item.pos()
                        self._drag_item_z = self._drag_item.zValue()
                        self._drag_payload = asset_name
                        self._drag_moved = False
                        self._drag_item.setZValue(1000)
                        self._drag_item.setOpacity(0.82)
                        self._drag_item.setCursor(Qt.ClosedHandCursor)
                        self.viewport().grabMouse()
                        event.accept()
                        return
                self.asset_clicked.emit(asset_name)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        """拖拽时移动图元；音量滑块拖动时直接发音量 signal。"""
        if self._music_volume_drag_item is not None:
            self._emit_music_volume_from_slider(
                self._music_volume_drag_item,
                self.mapToScene(event.pos()),
            )
            event.accept()
            return

        if self._drag_item is not None:
            scene_pos = self.mapToScene(event.pos())
            if (scene_pos - self._drag_press_scene_pos).manhattanLength() > 24:
                self._drag_moved = True
            self._drag_item.setPos(scene_pos - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        """释放时根据 payload 前缀分发到各工作台命中处理。"""
        if self._music_volume_drag_item is not None:
            self._emit_music_volume_from_slider(
                self._music_volume_drag_item,
                self.mapToScene(event.pos()),
            )
            self._music_volume_drag_item = None
            event.accept()
            return

        if self._drag_item is not None:
            scene_pos = self.mapToScene(event.pos())
            payload = self._drag_payload
            item = self._drag_item
            if not self._drag_moved:
                item.setPos(self._drag_item_start)
                item.setOpacity(1.0)
                item.setZValue(self._drag_item_z)
                item.setCursor(Qt.OpenHandCursor)
                self._drag_item = None
                self._drag_payload = ""
                self.viewport().releaseMouse()
                if self._reload_pending:
                    QTimer.singleShot(0, self.reload_scene)
                event.accept()
                return

            if payload.startswith("cheung_fun_spoon:"):
                self._release_cheung_fun_spoon(payload, scene_pos, item)
                event.accept()
                return

            if (
                payload.startswith("cheung_fun_ingredient:")
                or payload == "cheung_fun_spatula"
            ):
                self._release_cheung_fun_drag(payload, scene_pos, item)
                event.accept()
                return

            if payload.startswith("bbq_seasoning:"):
                self._release_bbq_seasoning(payload, scene_pos, item)
                event.accept()
                return

            if payload.startswith("bbq_skewer_source:"):
                self._release_bbq_skewer(payload, scene_pos, item)
                event.accept()
                return

            if payload.startswith("staple_ingredient:"):
                self._release_staple_ingredient(payload, scene_pos, item)
                event.accept()
                return

            pan_index = self._griddle_pan_index_at(scene_pos)
            dropped_on_griddle = pan_index >= 0

            if dropped_on_griddle:
                item.setVisible(False)
            else:
                self._animate_item_to_garbage(item)

            self._last_griddle_drop_item = item
            self._drag_item = None
            self._drag_payload = ""
            self.viewport().releaseMouse()
            key = payload.split(":", 2)[1] if ":" in payload else ""
            if key:
                self.griddle_ingredient_dropped.emit(key, pan_index)
            elif self._reload_pending:
                QTimer.singleShot(0, self.reload_scene)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _emit_music_volume_from_slider(self, item, scene_pos: QPointF) -> None:
        """把滑块场景坐标转换成 0-1 音量比例。"""
        rect = item.sceneBoundingRect()
        if rect.width() <= 0:
            return
        ratio = (scene_pos.x() - rect.x()) / rect.width()
        self.music_volume_changed.emit(_clamped_ratio(float(ratio)))
    def _release_cheung_fun_spoon(
        self,
        payload: str,
        scene_pos: QPointF,
        item: QGraphicsPixmapItem,
    ) -> None:
        """肠粉勺释放：空勺命中面糊区则装满，满勺命中烤台则倒面糊。"""
        spoon_state = payload.split(":", 1)[1] if ":" in payload else ""
        pan_index = self._cheung_fun_pan_index_at(scene_pos)

        self._drag_item = None
        self._drag_payload = ""
        self.viewport().releaseMouse()

        if spoon_state == "empty" and CHEUNG_FUN_BATTER_HOTZONE_RECT.contains(scene_pos):
            item.setVisible(False)
            self.cheung_fun_spoon_dropped.emit("fill", -1)
            return

        if spoon_state == "filled" and pan_index >= 0:
            item.setVisible(False)
            self.cheung_fun_spoon_dropped.emit("pour", pan_index)
            return

        self._animate_item_back_to_start(item)
    def _release_cheung_fun_drag(
        self,
        payload: str,
        scene_pos: QPointF,
        item: QGraphicsPixmapItem,
    ) -> None:
        """肠粉配料/铲勺释放：命中烤台则发对应 signal，否则回弹或丢垃圾桶。"""
        pan_index = self._cheung_fun_pan_index_at(scene_pos)

        self._drag_item = None
        self._drag_payload = ""
        self.viewport().releaseMouse()

        if pan_index < 0:
            ingredient_key = ""
            if payload.startswith("cheung_fun_ingredient:"):
                parts = payload.split(":", 2)
                ingredient_key = parts[1] if len(parts) > 1 else ""
            if ingredient_key == "shrimp":
                self._garbage_asset_name = "肠粉间的垃圾桶.png"
                self._animate_item_to_garbage(item)
                self.cheung_fun_ingredient_dropped.emit(ingredient_key, -1)
                return
            self._animate_item_back_to_start(item)
            return

        item.setVisible(False)
        if payload == "cheung_fun_spatula":
            self.cheung_fun_spatula_dropped.emit(pan_index)
            return

        parts = payload.split(":", 2)
        ingredient_key = parts[1] if len(parts) > 1 else ""
        if ingredient_key:
            self.cheung_fun_ingredient_dropped.emit(ingredient_key, pan_index)
        elif self._reload_pending:
            QTimer.singleShot(0, self.reload_scene)
    def _release_bbq_seasoning(
        self,
        payload: str,
        scene_pos: QPointF,
        item: QGraphicsPixmapItem,
    ) -> None:
        """调料释放：命中烧烤热区且有烤串时，发调味 signal 并播放撒料动画。"""
        parts = payload.split(":", 2)
        seasoning_key = parts[1] if len(parts) > 1 else ""

        self._drag_item = None
        self._drag_payload = ""
        self.viewport().releaseMouse()

        if not BBQ_GRILL_HOTZONE_RECT.contains(scene_pos):
            self._animate_item_back_to_start(item)
            return

        if not self._has_bbq_occupied_slot():
            self._animate_item_back_to_start(item)
            return

        item.setVisible(False)
        self.bbq_seasoning_dropped.emit(seasoning_key, -1)
        self._animate_bbq_seasoning_sprinkle(seasoning_key)
    def _release_bbq_skewer(
        self,
        payload: str,
        scene_pos: QPointF,
        item: QGraphicsPixmapItem,
    ) -> None:
        """烤串释放：吸附到最近可用槽位。"""
        parts = payload.split(":", 2)
        skewer_key = parts[1] if len(parts) > 1 else ""
        slot_index = self._nearest_bbq_slot_index(scene_pos)

        self._drag_item = None
        self._drag_payload = ""
        self.viewport().releaseMouse()

        if slot_index < 0:
            self._animate_item_back_to_start(item)
            return

        item.setVisible(False)
        self.bbq_skewer_dropped.emit(skewer_key, slot_index)

    def _release_staple_ingredient(
        self,
        payload: str,
        scene_pos: QPointF,
        item: QGraphicsPixmapItem,
    ) -> None:
        """主食素材释放：命中电饭煲槽位后发米/水投放 signal。"""
        parts = payload.split(":", 2)
        item_key = parts[1] if len(parts) > 1 else ""
        cooker_index = self._staple_cooker_index_at(scene_pos)

        self._drag_item = None
        self._drag_payload = ""
        self.viewport().releaseMouse()

        if cooker_index < 0:
            self._animate_item_back_to_start(item)
            return

        item.setVisible(False)
        self.staple_ingredient_dropped.emit(item_key, cooker_index)

    def _staple_cooker_index_at(self, scene_pos: QPointF) -> int:
        """返回命中的电饭煲槽位；未命中或不在主食场景时返回 -1。"""
        if self._scene_key != "staple_station":
            return -1

        for index in range(len(STAPLE_COOKER_SLOT_ASSET_NAMES)):
            if self.staple_cooker_rect(index).contains(scene_pos):
                return index
        return -1

    def staple_cooker_rect(self, index: int) -> QRectF:
        """电饭煲槽位矩形；优先读布局文件，缺失时用默认坐标。"""
        if 0 <= index < len(STAPLE_COOKER_SLOT_ASSET_NAMES):
            asset_name = STAPLE_COOKER_SLOT_ASSET_NAMES[index]
            if self.store.asset_metadata(asset_name):
                x, y, w, h, _layer = self.store.asset_geometry(asset_name)
                return QRectF(float(x), float(y), float(w), float(h))
            return STAPLE_DEFAULT_COOKER_RECTS[index]
        return QRectF()

    def _nearest_bbq_slot_index(self, scene_pos: QPointF) -> int:
        """找离释放点最近的可用烧烤槽位，距离过远则视为未命中。"""
        if self._scene_key != "bbq_station":
            return -1

        best_index = -1
        best_distance = BBQ_SLOT_SNAP_MAX_DISTANCE
        for index in range(len(BBQ_SLOT_ASSET_NAMES)):
            if self._is_bbq_slot_available is not None and not self._is_bbq_slot_available(index):
                continue
            rect = self.bbq_slot_rect(index)
            center = rect.center()
            distance = ((center.x() - scene_pos.x()) ** 2 + (center.y() - scene_pos.y()) ** 2) ** 0.5
            if distance <= best_distance:
                best_index = index
                best_distance = distance
        return best_index

    def _has_bbq_occupied_slot(self) -> bool:
        """调料只有在烤架上已有烤串时才允许释放。"""
        if self._scene_key != "bbq_station" or self._is_bbq_slot_available is None:
            return False

        for index in range(len(BBQ_SLOT_ASSET_NAMES)):
            if not self._is_bbq_slot_available(index):
                return True
        return False

    def bbq_slot_rect(self, index: int) -> QRectF:
        """烧烤槽位矩形；覆盖层也会用它决定烤串渲染位置。"""
        if 0 <= index < len(BBQ_SLOT_ASSET_NAMES):
            asset_name = BBQ_SLOT_ASSET_NAMES[index]
            if self.store.asset_metadata(asset_name):
                x, y, w, h, _layer = self.store.asset_geometry(asset_name)
                return QRectF(float(x), float(y), float(w), float(h))
            return BBQ_DEFAULT_SLOT_RECTS[index]
        return QRectF()

    def _animate_bbq_seasoning_sprinkle(
        self,
        seasoning_key: str,
        duration_ms: int = 1200,
    ) -> None:
        """播放调料罐横向移动和粒子下落动画，结束后重载场景。"""
        asset_name = BBQ_TILTED_SEASONING_ASSET_NAMES.get(seasoning_key)
        if asset_name is None or not self.store.asset_metadata(asset_name):
            self.reload_scene()
            return

        asset_x, asset_y, asset_w, asset_h, _layer = self.store.asset_geometry(asset_name)
        hotzone = BBQ_GRILL_HOTZONE_RECT
        can_y = int(asset_y)
        start_x = int(asset_x)
        end_x = int(hotzone.right() - asset_w - 220)
        particle_color = BBQ_SEASONING_PARTICLE_COLORS.get(seasoning_key, "#8B5A2B")

        can_item = QGraphicsPixmapItem(self._load_scaled_pixmap(asset_name, asset_w, asset_h))
        can_item.setPos(float(start_x), float(can_y))
        can_item.setZValue(1080)
        self.graphics_scene.addItem(can_item)

        particles: list[dict[str, Any]] = []
        started_at = time.monotonic()
        last_spawn_tick = -1
        can_removed = False
        timer = QTimer(self)
        timer.setInterval(16)

        def add_particle(spawn_x: float, spawn_y: float, size: int, lifetime_ms: int) -> None:
            path = QPainterPath()
            path.addEllipse(0.0, 0.0, float(size), float(size))
            particle = QGraphicsPathItem(path)
            particle.setBrush(QBrush(QColor(particle_color)))
            particle.setPen(QPen(QColor("transparent"), 0))
            particle.setPos(spawn_x, spawn_y)
            particle.setZValue(1070)
            self.graphics_scene.addItem(particle)
            particles.append(
                {
                    "item": particle,
                    "born_at": time.monotonic(),
                    "start": QPointF(spawn_x, spawn_y),
                    "end_y": float(hotzone.bottom()),
                    "drift": float((len(particles) % 7) - 3) * 18.0,
                    "lifetime": lifetime_ms / 1000.0,
                }
            )

        def tick() -> None:
            nonlocal can_removed, last_spawn_tick
            progress = min(1.0, (time.monotonic() - started_at) / (duration_ms / 1000.0))
            can_x = start_x + (end_x - start_x) * progress
            if can_item.scene() is self.graphics_scene:
                can_item.setPos(can_x, float(can_y))

            spawn_tick = int(progress * 54)
            if spawn_tick != last_spawn_tick and progress < 0.96:
                last_spawn_tick = spawn_tick
                pour_x = can_x + asset_w * 0.42
                pour_y = can_y + asset_h * 0.68
                for index in range(4):
                    size = 18 + ((spawn_tick + index) % 4) * 5
                    add_particle(
                        pour_x + (index - 1.5) * 42.0,
                        pour_y + (index % 2) * 28.0,
                        size,
                        520 + (index % 3) * 95,
                    )

            if progress >= 1.0 and not can_removed:
                can_removed = True
                if can_item.scene() is self.graphics_scene:
                    self.graphics_scene.removeItem(can_item)

            now = time.monotonic()
            for particle in particles[:]:
                particle_item = particle["item"]
                age = now - float(particle["born_at"])
                lifetime = max(0.001, float(particle["lifetime"]))
                particle_progress = min(1.0, age / lifetime)
                start = particle["start"]
                end_y = float(particle["end_y"])
                if particle_item.scene() is self.graphics_scene:
                    particle_item.setPos(
                        start.x() + float(particle["drift"]) * particle_progress,
                        start.y() + (end_y - start.y()) * particle_progress,
                    )
                    particle_item.setOpacity(1.0 - particle_progress)
                if particle_progress >= 1.0:
                    if particle_item.scene() is self.graphics_scene:
                        self.graphics_scene.removeItem(particle_item)
                    particles.remove(particle)

            if progress >= 1.0 and not particles:
                timer.stop()
                if timer in self._bbq_seasoning_timers:
                    self._bbq_seasoning_timers.remove(timer)
                if self._reload_pending:
                    QTimer.singleShot(0, self.reload_scene)
                else:
                    self.reload_scene()

        timer.timeout.connect(tick)
        self._bbq_seasoning_timers.append(timer)
        timer.start()

    def _cheung_fun_pan_index_at(self, scene_pos: QPointF) -> int:
        """返回命中的肠粉烤台索引；未命中或不在肠粉场景时返回 -1。"""
        if self._scene_key != "cheung_fun_station":
            return -1

        for index, rect in enumerate(CHEUNG_FUN_PAN_RECTS):
            if rect.contains(scene_pos):
                return index
        return -1

    def _animate_item_back_to_start(
        self,
        item: QGraphicsPixmapItem,
        duration_ms: int = 180,
    ) -> None:
        """投放失败时把拖拽物平滑弹回原位。"""
        start_pos = item.pos()
        end_pos = QPointF(self._drag_item_start)
        original_z = self._drag_item_z
        started_at = time.monotonic()
        timer = QTimer(self)
        timer.setInterval(16)

        def tick() -> None:
            progress = min(1.0, (time.monotonic() - started_at) / (duration_ms / 1000.0))
            eased = 1.0 - (1.0 - progress) * (1.0 - progress)
            if item.scene() is self.graphics_scene:
                item.setPos(start_pos + (end_pos - start_pos) * eased)
                item.setOpacity(0.82 + 0.18 * progress)

            if progress >= 1.0:
                timer.stop()
                if timer in self._return_timers:
                    self._return_timers.remove(timer)
                if item.scene() is self.graphics_scene:
                    item.setPos(end_pos)
                    item.setOpacity(1.0)
                    item.setZValue(original_z)
                    item.setCursor(Qt.OpenHandCursor)
                if self._reload_pending:
                    QTimer.singleShot(0, self.reload_scene)

        timer.timeout.connect(tick)
        self._return_timers.append(timer)
        timer.start()

    def _griddle_pan_index_at(self, scene_pos: QPointF) -> int:
        """返回命中的烤盘索引；未命中或不在烤盘场景时返回 -1。"""
        if self._scene_key != "griddle_station":
            return -1

        for index in range(len(GRIDDLE_PAN_RECTS)):
            if self.griddle_pan_rect(index).contains(scene_pos):
                return index
        return -1

    def griddle_pan_rect(self, index: int) -> QRectF:
        """烤盘矩形；优先读布局文件，缺失时用默认坐标。"""
        if 0 <= index < len(GRIDDLE_PAN_ASSET_NAMES):
            asset_name = GRIDDLE_PAN_ASSET_NAMES[index]
            if self.store.asset_metadata(asset_name):
                x, y, w, h, _layer = self.store.asset_geometry(asset_name)
                return QRectF(float(x), float(y), float(w), float(h))
        return GRIDDLE_PAN_RECTS[index]

    def flash_last_griddle_drop_to_garbage(self) -> None:
        """烤盘投放被业务层拒绝时，让刚拖的食材落入垃圾桶淡出。"""
        item = self._last_griddle_drop_item
        if item is None or item.scene() is not self.graphics_scene:
            QTimer.singleShot(0, self.reload_scene)
            return

        self._animate_item_to_garbage(item)

    def _animate_item_to_garbage(self, item: QGraphicsPixmapItem, duration_ms: int = 2000) -> None:
        """把素材移动到当前垃圾桶位置并淡出。"""
        garbage_asset_name = self._garbage_asset_name
        self._garbage_asset_name = "烤盘间的垃圾桶.png"
        item.setVisible(True)
        item.setPos(self._garbage_position(item, garbage_asset_name))
        item.setOpacity(1.0)
        item.setZValue(1000)
        item.setTransformOriginPoint(item.boundingRect().center())
        item.setScale(0.7)

        started_at = time.monotonic()
        timer = QTimer(self)
        timer.setInterval(33)

        def tick() -> None:
            progress = min(1.0, (time.monotonic() - started_at) / (duration_ms / 1000.0))
            if item.scene() is self.graphics_scene:
                item.setOpacity(1.0 - progress)

            if progress >= 1.0:
                timer.stop()
                if timer in self._garbage_fade_timers:
                    self._garbage_fade_timers.remove(timer)
                self.reload_scene()

        timer.timeout.connect(tick)
        self._garbage_fade_timers.append(timer)
        timer.start()

    def _garbage_position(
        self,
        item: QGraphicsPixmapItem | None = None,
        garbage_asset_name: str = "烤盘间的垃圾桶.png",
    ) -> QPointF:
        """计算垃圾桶中心放置点；素材缺失时回到拖拽起点。"""
        metadata = self.store.asset_metadata(garbage_asset_name)
        if metadata:
            x, y, w, h, _layer = self.store.asset_geometry(garbage_asset_name)
            if item is not None:
                item_rect = item.boundingRect()
                return QPointF(
                    float(x) + max(0.0, (float(w) - item_rect.width()) / 2.0),
                    float(y) + max(0.0, (float(h) - item_rect.height()) / 2.0),
                )
            return QPointF(float(x), float(y))
        return self._drag_item_start
