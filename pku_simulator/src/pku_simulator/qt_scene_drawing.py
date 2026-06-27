"""`GameSceneView` 的绘制工具方法。

覆盖层模块只需要调用 `add_asset_item/add_rect_item/add_text_item` 等接口，不需要
直接操作 Qt 图元创建细节。
"""

from __future__ import annotations

import html

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QPixmap, QTransform
from PySide6.QtWidgets import (
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
)

from pku_simulator.layout_editor import asset_visual_transform


class SceneDrawingMixin:
    """图片、形状、文字和视图缩放的统一 helper。"""

    def _fit_current_scene(self) -> None:
        """按当前 scene 适配视口；商店允许纵向滚动，其它场景完整缩放。"""
        scene_rect = self.graphics_scene.sceneRect()
        if scene_rect.isEmpty():
            return

        if self._scene_key == "shop_screen":
            self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scale = self.viewport().width() / max(1.0, scene_rect.width())
            transform = QTransform()
            transform.scale(scale, scale)
            self.setTransform(transform)
            return

        self.setAlignment(Qt.AlignCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.fitInView(scene_rect, Qt.KeepAspectRatio)

    def visible_scene_rect(self) -> QRectF:
        """返回当前视口在场景坐标中的可见区域，商店覆盖层用于跟随滚动。"""
        return self.mapToScene(self.viewport().rect()).boundingRect()

    def _load_pixmap(self, asset_name: str, width: int, height: int) -> QPixmap:
        """读取原始图片；失败时返回灰色占位图。"""
        path = self.store.resolve_asset_path(asset_name)
        if path is not None:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return pixmap

        fallback = QPixmap(max(1, width), max(1, height))
        fallback.fill(Qt.darkGray)
        return fallback

    def _load_scaled_pixmap(self, asset_name: str, width: int, height: int) -> QPixmap:
        """读取并缩放图片；按路径、mtime 和尺寸缓存，减少重绘开销。"""
        target_w = max(1, width)
        target_h = max(1, height)
        path = self.store.resolve_asset_path(asset_name)
        if path is not None:
            try:
                cache_key = (
                    str(path),
                    path.stat().st_mtime_ns,
                    target_w,
                    target_h,
                )
            except OSError:
                cache_key = (
                    str(path),
                    0,
                    target_w,
                    target_h,
                )
            cached = self._pixmap_cache.get(cache_key)
            if cached is not None and not cached.isNull():
                return cached

            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                if pixmap.width() == target_w and pixmap.height() == target_h:
                    scaled = pixmap
                else:
                    scaled = pixmap.scaled(
                        target_w,
                        target_h,
                        Qt.IgnoreAspectRatio,
                        Qt.SmoothTransformation,
                    )
                self._pixmap_cache[cache_key] = scaled
                return scaled

        fallback = QPixmap(target_w, target_h)
        fallback.fill(Qt.darkGray)
        return fallback

    def _apply_asset_visual_transform(
        self,
        item: QGraphicsPixmapItem,
        asset_name: str,
        width: int,
        height: int,
    ) -> None:
        """应用布局文件中的旋转/透视参数。"""
        rotation, perspective = self.store.asset_transform(asset_name)
        item.setTransform(
            asset_visual_transform(width, height, rotation, perspective)
        )

    def add_asset_item(
        self,
        asset_name: str,
        x: int,
        y: int,
        width: int | None = None,
        height: int | None = None,
        layer: int = 100,
        data: str | None = None,
    ) -> QGraphicsPixmapItem | None:
        """在场景中添加图片图元；覆盖层按钮也通过 data 字段暴露点击接口。"""
        metadata = self.store.asset_metadata(asset_name)
        if not metadata:
            return None

        default_x, default_y, default_w, default_h, _default_layer = self.store.asset_geometry(asset_name)
        del default_x, default_y
        target_w = width or default_w
        target_h = height or default_h
        item = QGraphicsPixmapItem(self._load_scaled_pixmap(asset_name, target_w, target_h))
        self._apply_asset_visual_transform(item, asset_name, target_w, target_h)
        item.setPos(float(x), float(y))
        item.setZValue(float(layer))
        item.setData(0, data or asset_name)
        self.graphics_scene.addItem(item)
        if self._rendering_overlay:
            self._overlay_items.append(item)
        return item

    def add_rect_item(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        fill: str,
        outline: str = "transparent",
        layer: int = 200,
        data: str | None = None,
        outline_width: int = 1,
    ) -> QGraphicsRectItem:
        """添加矩形图元；常用于按钮背景、遮罩和进度条。"""
        item = QGraphicsRectItem(QRectF(float(x), float(y), float(width), float(height)))
        item.setBrush(QBrush(QColor(fill)))
        item.setPen(QPen(QColor(outline), outline_width))
        item.setZValue(float(layer))
        if data is not None:
            item.setData(0, data)
        self.graphics_scene.addItem(item)
        if self._rendering_overlay:
            self._overlay_items.append(item)
        return item

    def add_rounded_rect_item(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        radius: int,
        fill: str,
        outline: str = "transparent",
        layer: int = 200,
        data: str | None = None,
        outline_width: int = 1,
    ) -> QGraphicsPathItem:
        """添加圆角矩形图元；覆盖层信息框使用。"""
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(float(x), float(y), float(width), float(height)),
            float(radius),
            float(radius),
        )
        item = QGraphicsPathItem(path)
        item.setBrush(QBrush(QColor(fill)))
        item.setPen(QPen(QColor(outline), outline_width))
        item.setZValue(float(layer))
        if data is not None:
            item.setData(0, data)
        self.graphics_scene.addItem(item)
        if self._rendering_overlay:
            self._overlay_items.append(item)
        return item

    def add_ellipse_item(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        fill: str,
        outline: str = "transparent",
        layer: int = 200,
        data: str | None = None,
        outline_width: int = 1,
    ) -> QGraphicsPathItem:
        """添加椭圆图元；烟雾、粒子等效果使用。"""
        path = QPainterPath()
        path.addEllipse(QRectF(float(x), float(y), float(width), float(height)))
        item = QGraphicsPathItem(path)
        item.setBrush(QBrush(QColor(fill)))
        item.setPen(QPen(QColor(outline), outline_width))
        item.setZValue(float(layer))
        if data is not None:
            item.setData(0, data)
        self.graphics_scene.addItem(item)
        if self._rendering_overlay:
            self._overlay_items.append(item)
        return item

    def add_path_stroke_item(
        self,
        path: QPainterPath,
        color: str,
        width: int,
        layer: int = 200,
        data: str | None = None,
    ) -> QGraphicsPathItem:
        """添加路径描边；用于简单手绘线条或装饰线。"""
        item = QGraphicsPathItem(path)
        pen = QPen(QColor(color), max(1, width))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        item.setPen(pen)
        item.setBrush(QBrush(Qt.NoBrush))
        item.setZValue(float(layer))
        if data is not None:
            item.setData(0, data)
        self.graphics_scene.addItem(item)
        if self._rendering_overlay:
            self._overlay_items.append(item)
        return item

    def add_text_item(
        self,
        text: str,
        x: int,
        y: int,
        size: int,
        color: str = "#1f2937",
        layer: int = 200,
        data: str | None = None,
        bold: bool = False,
        width: int | None = None,
        align_center: bool = False,
    ) -> QGraphicsTextItem:
        """添加文字图元；`width/align_center` 用于票据和按钮文字排版。"""
        item = QGraphicsTextItem(text)
        font = QFont()
        font.setPointSize(size)
        font.setBold(bold)
        item.setFont(font)
        if width is not None:
            item.setTextWidth(float(width))
        if align_center:
            item.setHtml(
                f'<div align="center" style="color: {color};">'
                f"{html.escape(text)}"
                "</div>"
            )
        else:
            item.setDefaultTextColor(color)
        item.setPos(float(x), float(y))
        item.setZValue(float(layer))
        if data is not None:
            item.setData(0, data)
        self.graphics_scene.addItem(item)
        if self._rendering_overlay:
            self._overlay_items.append(item)
        return item
