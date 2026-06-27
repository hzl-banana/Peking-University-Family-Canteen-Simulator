"""资源布局编辑器。

这是嵌在主窗口里的开发辅助面板，用来读取/写回 `assets/asset_positions.json`。
运行时场景通过 `AssetLayoutStore` 取素材路径、坐标、尺寸、层级和变换；编辑器
则通过拖拽图元和右侧输入框修改同一份布局数据。
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygonF, QTransform
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal

from pku_simulator.core.config import CANVAS_HEIGHT, CANVAS_WIDTH

SCENE_SHARED_SCENES = {
    "start_screen": {"global_overlay"},
    "shop_screen": {"global_overlay"},
    "griddle_station": {"shared", "shared_ingredients", "global_overlay"},
    "cheung_fun_station": {"shared", "global_overlay"},
    "staple_station": {"shared", "global_overlay"},
    "bbq_station": {"shared", "global_overlay"},
    "counter_station": {"global_overlay"},
}
"""每个场景需要额外显示的共享资源分组。"""

RUNTIME_ONLY_ASSET_NAMES = {
    "计时器背景.jpg",
    "出锅红色背景按钮.jpg",
    "出锅灰色背景按钮.jpg",
}
"""运行时动态生成或不适合拖拽编辑的素材名。"""

MAX_PERSPECTIVE_DEGREES = 80.0


class AssetLayoutStore:
    """封装 asset_positions.json 的读取、容错、查询和写回接口。"""

    def __init__(self, json_path: Path, project_root: Path) -> None:
        """绑定布局 JSON 与项目根目录，初始化时立即加载数据。"""
        self.json_path = json_path
        self.project_root = project_root
        self._data: dict[str, Any] = {}
        self._assets: dict[str, dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """从磁盘读取布局；文件缺失或结构异常时使用空布局兜底。"""
        if not self.json_path.exists():
            self._data = {"meta": {}, "assets": {}}
            self._assets = {}
            return

        with self.json_path.open("r", encoding="utf-8") as f:
            self._data = json.load(f)

        raw_assets = self._data.get("assets", {})
        if not isinstance(raw_assets, dict):
            raw_assets = {}
            self._data["assets"] = raw_assets
        self._assets = raw_assets

    def save(self) -> None:
        """把当前布局数据写回 JSON，供运行时场景下一次刷新使用。"""
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        with self.json_path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    def scene_names(self) -> list[str]:
        """收集 JSON 中出现过的场景 key，用于场景下拉框。"""
        names: set[str] = set()
        for asset in self._assets.values():
            scene = str(asset.get("scene", "")).strip()
            if scene:
                names.add(scene)
        return sorted(names)

    def scene_asset_names(self, scene_key: str, include_shared: bool = True) -> list[str]:
        """返回某个场景需要编辑的素材名，可选择包含共享分组。"""
        scene_key = scene_key.strip()
        if not scene_key:
            return []

        accepted = {scene_key}
        if include_shared:
            accepted |= SCENE_SHARED_SCENES.get(scene_key, set())

        matched: list[str] = []
        for name, asset in self._assets.items():
            scene = str(asset.get("scene", "")).strip()
            if scene in accepted:
                matched.append(name)

        matched.sort(key=self._sort_key)
        return matched

    def asset_metadata(self, asset_name: str) -> dict[str, Any]:
        """返回素材原始元数据；调用方用它判断 visible/path 等字段。"""
        asset = self._assets.get(asset_name)
        return asset if isinstance(asset, dict) else {}

    def shop_glass_opacity(self) -> float:
        """读取商店玻璃卡片透明度设置，供商店 overlay 和编辑器滑块共用。"""
        meta = self._data.setdefault("meta", {})
        if not isinstance(meta, dict):
            meta = {}
            self._data["meta"] = meta
        value = _safe_float(meta.get("shop_glass_opacity"), 0.27)
        return max(0.0, min(1.0, value))

    def update_shop_glass_opacity(self, opacity: float) -> None:
        """更新商店玻璃卡片透明度，实际保存由 `save()` 负责。"""
        meta = self._data.setdefault("meta", {})
        if not isinstance(meta, dict):
            meta = {}
            self._data["meta"] = meta
        meta["shop_glass_opacity"] = round(max(0.0, min(1.0, float(opacity))), 3)

    def resolve_asset_path(self, asset_name: str) -> Path | None:
        """把布局里的相对路径解析成真实文件路径，并兼容同名不同图片后缀。"""
        asset = self._assets.get(asset_name)
        if asset is None:
            return None

        rel_path = asset.get("path")
        if not isinstance(rel_path, str) or not rel_path.strip():
            return None

        resolved = self.project_root / rel_path
        if resolved.exists():
            return resolved

        # 允许占位图被同名的 jpg/png/webp 等图片替换，避免 JSON 改路径。
        image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        if resolved.suffix.lower() in image_suffixes and resolved.parent.exists():
            for candidate in resolved.parent.iterdir():
                if (
                    candidate.is_file()
                    and candidate.stem == resolved.stem
                    and candidate.suffix.lower() in image_suffixes
                ):
                    return candidate

        return None

    def asset_geometry(self, asset_name: str) -> tuple[int, int, int, int, int]:
        """读取素材的 x/y/width/height/layer，并对缺失值给默认值。"""
        asset = self._assets.get(asset_name, {})
        pos = asset.get("position", {})
        if not isinstance(pos, dict):
            pos = {}

        x = _safe_int(pos.get("x"), 0)
        y = _safe_int(pos.get("y"), 0)
        w = max(1, _safe_int(pos.get("width"), 120))
        h = max(1, _safe_int(pos.get("height"), 120))
        layer = _safe_int(pos.get("layer"), 0)
        return x, y, w, h, layer

    def asset_transform(self, asset_name: str) -> tuple[float, float]:
        """读取素材的旋转和透视压平参数。"""
        asset = self._assets.get(asset_name, {})
        pos = asset.get("position", {})
        if not isinstance(pos, dict):
            pos = {}

        rotation = _safe_float(pos.get("rotation"), 0.0)
        perspective = _safe_float(pos.get("perspective"), 0.0)
        return rotation, perspective

    def update_asset_geometry(
        self,
        asset_name: str,
        x: int,
        y: int,
        width: int,
        height: int,
        layer: int,
    ) -> None:
        """更新素材几何信息；由拖拽回调和右侧输入框共同调用。"""
        asset = self._assets.get(asset_name)
        if asset is None:
            return

        pos = asset.setdefault("position", {})
        if not isinstance(pos, dict):
            pos = {}
            asset["position"] = pos

        pos["x"] = int(x)
        pos["y"] = int(y)
        pos["width"] = max(1, int(width))
        pos["height"] = max(1, int(height))
        pos["layer"] = int(layer)

    def update_asset_transform(
        self,
        asset_name: str,
        rotation: float,
        perspective: float,
    ) -> None:
        """更新素材视觉变换；接近 0 的参数会从 JSON 中移除。"""
        asset = self._assets.get(asset_name)
        if asset is None:
            return

        pos = asset.setdefault("position", {})
        if not isinstance(pos, dict):
            pos = {}
            asset["position"] = pos

        _set_optional_float(pos, "rotation", rotation)
        _set_optional_float(pos, "perspective", perspective)

    def _sort_key(self, asset_name: str) -> tuple[int, int, str]:
        """按图层、显式 order、名称排序，保证编辑器列表和场景叠放稳定。"""
        asset = self._assets.get(asset_name, {})
        pos = asset.get("position", {})
        if not isinstance(pos, dict):
            pos = {}
        layer = _safe_int(pos.get("layer"), 0)
        order = _safe_int(asset.get("order"), 0)
        return (layer, order, asset_name)


class _AutoFitGraphicsView(QGraphicsView):
    """自动把 scene 缩放到视口内的预览画布。"""

    def __init__(self, scene: QGraphicsScene) -> None:
        """初始化黑底、无滚动条、居中缩放的视图。"""
        super().__init__(scene)
        self.setAlignment(Qt.AlignCenter)
        self.setBackgroundBrush(QColor("#000000"))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """窗口尺寸变化时重新 fitInView，避免预览画布被裁切。"""
        super().resizeEvent(event)
        scene = self.scene()
        if scene is not None:
            self.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)


class _DraggableAssetItem(QGraphicsPixmapItem):
    """可拖拽素材图元，负责把移动/选中事件回传给编辑器。"""

    def __init__(
        self,
        asset_name: str,
        source_pixmap: QPixmap,
        on_move: Callable[[str, float, float], None],
        on_selected: Callable[[str], None],
    ) -> None:
        """保存回调和原始 pixmap，并开启 Qt 的移动/选中通知。"""
        super().__init__()
        self.asset_name = asset_name
        self._source_pixmap = source_pixmap
        self._on_move = on_move
        self._on_selected = on_selected
        self._last_render_size: tuple[int, int] | None = None
        self._rotation = 0.0
        self._perspective = 0.0

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def set_render_size(self, width: int, height: int) -> None:
        """按布局尺寸重绘 pixmap；尺寸未变化时跳过缩放。"""
        target_w = max(1, int(width))
        target_h = max(1, int(height))
        render_size = (target_w, target_h)
        if self._last_render_size == render_size:
            return

        if self._source_pixmap.width() == target_w and self._source_pixmap.height() == target_h:
            pixmap = self._source_pixmap
        else:
            pixmap = self._source_pixmap.scaled(
                target_w,
                target_h,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
        self.setPixmap(pixmap)
        self._last_render_size = render_size
        self._apply_visual_transform()

    def set_visual_transform(self, rotation: float, perspective: float) -> None:
        """设置旋转/透视参数，并立即应用到当前 pixmap。"""
        self._rotation = float(rotation)
        self._perspective = float(perspective)
        self._apply_visual_transform()

    def _apply_visual_transform(self) -> None:
        """把 `asset_visual_transform()` 生成的 QTransform 应用到图元。"""
        pixmap = self.pixmap()
        if pixmap.isNull():
            self.setTransform(QTransform())
            return

        self.setTransform(
            asset_visual_transform(
                pixmap.width(),
                pixmap.height(),
                self._rotation,
                self._perspective,
            )
        )

    def itemChange(self, change, value):  # type: ignore[override]
        """Qt 图元事件入口：移动时更新坐标，选中时同步右侧表单。"""
        if change == QGraphicsItem.ItemPositionHasChanged:
            pos = self.pos()
            self._on_move(self.asset_name, float(pos.x()), float(pos.y()))
        elif change == QGraphicsItem.ItemSelectedHasChanged and bool(value):
            self._on_selected(self.asset_name)
        return super().itemChange(change, value)


class SceneLayoutEditor(QWidget):
    """主布局编辑器控件，连接场景列表、画布预览和参数表单。"""

    layout_changed = Signal()

    def __init__(
        self,
        store: AssetLayoutStore,
        is_asset_visible: Callable[[str], bool] | None = None,
        is_asset_rendered: Callable[[str, str], bool] | None = None,
    ) -> None:
        """创建编辑器 UI，并接入运行时可见性/渲染策略回调。"""
        super().__init__()
        self.store = store
        self._is_asset_visible = is_asset_visible or (lambda _asset_name: True)
        self._is_asset_rendered = is_asset_rendered or (
            lambda _asset_name, _scene_key: True
        )

        self._syncing = False
        self._items: dict[str, _DraggableAssetItem] = {}
        self._pixmap_cache: dict[tuple[str, int], QPixmap] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        top_row = QHBoxLayout()
        title = QLabel("场景拖拽布局")
        title.setStyleSheet("font-size: 15px; font-weight: 700;")

        self.scene_combo = QComboBox()
        self.scene_combo.setMinimumWidth(170)
        self.scene_combo.currentTextChanged.connect(self._reload_scene)

        self.reload_button = QPushButton("重载JSON")
        self.reload_button.clicked.connect(self._reload_from_disk)

        self.save_button = QPushButton("保存坐标")
        self.save_button.clicked.connect(self._save_layout)

        self.inventory_preview_check = QCheckBox("按库存预览")
        self.inventory_preview_check.setChecked(False)
        self.inventory_preview_check.toggled.connect(
            lambda _checked: self._reload_scene(self.scene_combo.currentText())
        )

        top_row.addWidget(title)
        top_row.addStretch(1)
        top_row.addWidget(QLabel("场景:"))
        top_row.addWidget(self.scene_combo)
        top_row.addWidget(self.inventory_preview_check)
        top_row.addWidget(self.reload_button)
        top_row.addWidget(self.save_button)

        self.graphics_scene = QGraphicsScene(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, self)
        self.graphics_view = _AutoFitGraphicsView(self.graphics_scene)
        self.graphics_view.setMinimumHeight(300)
        self.graphics_view.setStyleSheet(
            "QGraphicsView {"
            "background-color: #000000;"
            "border: 1px solid #334155;"
            "border-radius: 8px;"
            "}"
        )

        self.asset_combo = QComboBox()
        self.asset_combo.currentTextChanged.connect(self._select_asset_from_combo)

        self.x_spin = QSpinBox()
        self.x_spin.setRange(-20000, 20000)
        self.x_spin.valueChanged.connect(self._apply_spin_values)

        self.y_spin = QSpinBox()
        self.y_spin.setRange(-20000, 20000)
        self.y_spin.valueChanged.connect(self._apply_spin_values)

        self.w_spin = QSpinBox()
        self.w_spin.setRange(1, 20000)
        self.w_spin.valueChanged.connect(self._apply_spin_values)

        self.h_spin = QSpinBox()
        self.h_spin.setRange(1, 20000)
        self.h_spin.valueChanged.connect(self._apply_spin_values)

        self.layer_spin = QSpinBox()
        self.layer_spin.setRange(-100, 2000)
        self.layer_spin.valueChanged.connect(self._apply_spin_values)

        self.rotation_spin = QDoubleSpinBox()
        self.rotation_spin.setRange(-360.0, 360.0)
        self.rotation_spin.setDecimals(1)
        self.rotation_spin.setSingleStep(1.0)
        self.rotation_spin.setSuffix("°")
        self.rotation_spin.valueChanged.connect(self._apply_spin_values)

        self.perspective_spin = QDoubleSpinBox()
        self.perspective_spin.setRange(-MAX_PERSPECTIVE_DEGREES, MAX_PERSPECTIVE_DEGREES)
        self.perspective_spin.setDecimals(1)
        self.perspective_spin.setSingleStep(1.0)
        self.perspective_spin.setSuffix("°")
        self.perspective_spin.valueChanged.connect(self._apply_spin_values)

        self.shop_glass_slider = QSlider(Qt.Horizontal)
        self.shop_glass_slider.setRange(0, 100)
        self.shop_glass_slider.setSingleStep(1)
        self.shop_glass_slider.setPageStep(5)
        self.shop_glass_slider.valueChanged.connect(self._apply_shop_glass_opacity)
        self.shop_glass_value_label = QLabel("27%")
        self.shop_glass_value_label.setMinimumWidth(52)
        shop_glass_row = QHBoxLayout()
        shop_glass_row.addWidget(self.shop_glass_slider, 1)
        shop_glass_row.addWidget(self.shop_glass_value_label)

        controls = QFormLayout()
        controls.addRow("资源:", self.asset_combo)
        controls.addRow("x:", self.x_spin)
        controls.addRow("y:", self.y_spin)
        controls.addRow("width:", self.w_spin)
        controls.addRow("height:", self.h_spin)
        controls.addRow("layer:", self.layer_spin)
        controls.addRow("旋转角度:", self.rotation_spin)
        controls.addRow("透视压平角度:", self.perspective_spin)
        controls.addRow("商店玻璃不透明度:", shop_glass_row)

        self.status_label = QLabel("拖动图片调整位置，点击保存坐标写回 asset_positions.json")
        self.status_label.setStyleSheet("font-size: 12px; color: #64748b;")

        root.addLayout(top_row)
        root.addWidget(self.graphics_view)
        root.addLayout(controls)
        root.addWidget(self.status_label)

        self._reload_from_disk()

    def set_scene_key(self, scene_key: str) -> None:
        """外部切换主场景时同步编辑器场景下拉框。"""
        scene_key = scene_key.strip()
        if not scene_key:
            return

        index = self.scene_combo.findText(scene_key)
        if index < 0:
            return
        if self.scene_combo.currentIndex() != index:
            self.scene_combo.setCurrentIndex(index)

    def _reload_from_disk(self) -> None:
        """重新读取 JSON 并刷新场景列表，保留当前选中的场景。"""
        current_scene = self.scene_combo.currentText().strip()
        self.store.load()

        scene_names = [
            name
            for name in self.store.scene_names()
            if not name.startswith("disabled_")
        ]
        self.scene_combo.blockSignals(True)
        self.scene_combo.clear()
        self.scene_combo.addItems(scene_names)
        self.scene_combo.blockSignals(False)

        if current_scene and current_scene in scene_names:
            self.scene_combo.setCurrentText(current_scene)
        elif scene_names:
            self.scene_combo.setCurrentIndex(0)
        else:
            self._reload_scene("")
        self._sync_shop_glass_slider()

    def _reload_scene(self, scene_key: str) -> None:
        """根据场景 key 重建预览画布、素材列表和右侧控件状态。"""
        self.graphics_scene.clear()
        self._items.clear()

        scene_key = scene_key.strip()
        if not scene_key:
            self.asset_combo.clear()
            self._set_status("未找到可编辑场景。", success=False)
            self._sync_shop_glass_slider()
            return

        names = [
            name
            for name in self.store.scene_asset_names(scene_key, include_shared=True)
            if name not in RUNTIME_ONLY_ASSET_NAMES
            and bool(self.store.asset_metadata(name).get("visible", True))
            and self._is_asset_rendered(name, scene_key)
        ]
        if self.inventory_preview_check.isChecked():
            names = [name for name in names if self._is_asset_visible(name)]
        self.asset_combo.blockSignals(True)
        self.asset_combo.clear()

        for name in names:
            x, y, w, h, layer = self.store.asset_geometry(name)
            rotation, perspective = self.store.asset_transform(name)
            pixmap = self._load_pixmap(name, w, h)
            item = _DraggableAssetItem(name, pixmap, self._on_item_moved, self._on_item_selected)
            item.set_render_size(w, h)
            item.set_visual_transform(rotation, perspective)
            item.setPos(float(x), float(y))
            item.setZValue(float(layer))
            self.graphics_scene.addItem(item)
            self._items[name] = item
            self.asset_combo.addItem(name)

        self._resize_scene_to_items(names)
        self.asset_combo.blockSignals(False)

        if names:
            self.asset_combo.setCurrentIndex(0)
            self._select_asset(names[0])
            self._set_status(f"已加载 {len(names)} 个资源，可直接拖动。", success=True)
        else:
            self._set_status("该场景没有可编辑资源。", success=False)

        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.KeepAspectRatio)
        self._sync_shop_glass_slider()

    def _resize_scene_to_items(self, asset_names: list[str]) -> None:
        """根据当前素材外接范围扩展 scene，方便编辑超出默认画布的图层。"""
        if not asset_names:
            self.graphics_scene.setSceneRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
            return

        width = 1
        height = 1
        for name in asset_names:
            x, y, w, h, _layer = self.store.asset_geometry(name)
            width = max(width, x + w)
            height = max(height, y + h)

        self.graphics_scene.setSceneRect(0, 0, width, height)

    def _load_pixmap(self, asset_name: str, width: int, height: int) -> QPixmap:
        """读取素材图片并按文件 mtime 缓存；找不到图片时生成占位图。"""
        path = self.store.resolve_asset_path(asset_name)
        if path is not None:
            try:
                cache_key = (str(path), path.stat().st_mtime_ns)
            except OSError:
                cache_key = (str(path), 0)
            pixmap = self._pixmap_cache.get(cache_key)
            if pixmap is None:
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    self._pixmap_cache[cache_key] = pixmap
            if pixmap is not None and not pixmap.isNull():
                return pixmap
        return self._placeholder_pixmap(asset_name, width, height)

    def _placeholder_pixmap(self, asset_name: str, width: int, height: int) -> QPixmap:
        """为缺失素材绘制深色占位图，显示素材名方便排查资源路径。"""
        pixmap = QPixmap(max(120, width), max(80, height))
        pixmap.fill(QColor("#1e293b"))

        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor("#94a3b8")))
        painter.drawRect(0, 0, pixmap.width() - 1, pixmap.height() - 1)
        painter.setPen(QColor("#e2e8f0"))
        painter.drawText(pixmap.rect(), Qt.AlignCenter | Qt.TextWordWrap, asset_name)
        painter.end()
        return pixmap

    def _on_item_selected(self, asset_name: str) -> None:
        """拖拽画布选中图元时，同步下拉框和右侧参数表单。"""
        if self._syncing:
            return
        self._select_asset(asset_name)

    def _on_item_moved(self, asset_name: str, x: float, y: float) -> None:
        """拖动素材后更新 JSON 内存数据，并把新坐标同步到输入框。"""
        if self._syncing:
            return

        old_x, old_y, w, h, layer = self.store.asset_geometry(asset_name)
        new_x = int(round(x))
        new_y = int(round(y))
        if new_x == old_x and new_y == old_y:
            return

        self.store.update_asset_geometry(asset_name, new_x, new_y, w, h, layer)
        self.layout_changed.emit()
        if self.asset_combo.currentText() == asset_name:
            self._syncing = True
            self.x_spin.setValue(new_x)
            self.y_spin.setValue(new_y)
            self._syncing = False

        self._set_status(f"{asset_name} 已移动到 ({new_x}, {new_y})，记得保存。", success=False)

    def _select_asset_from_combo(self, asset_name: str) -> None:
        """素材下拉框变化入口，转到统一的选中逻辑。"""
        self._select_asset(asset_name)

    def _select_asset(self, asset_name: str) -> None:
        """选中某个素材：填充表单、选中画布图元并避免递归触发回调。"""
        item = self._items.get(asset_name)
        if item is None:
            return

        self._syncing = True
        combo_index = self.asset_combo.findText(asset_name)
        if combo_index >= 0 and self.asset_combo.currentIndex() != combo_index:
            self.asset_combo.setCurrentIndex(combo_index)

        x, y, w, h, layer = self.store.asset_geometry(asset_name)
        rotation, perspective = self.store.asset_transform(asset_name)
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)
        self.w_spin.setValue(w)
        self.h_spin.setValue(h)
        self.layer_spin.setValue(layer)
        self.rotation_spin.setValue(rotation)
        self.perspective_spin.setValue(perspective)

        for other in self._items.values():
            other.setSelected(False)
        item.setSelected(True)
        self._syncing = False

    def _apply_spin_values(self) -> None:
        """右侧表单变化入口：更新素材坐标/尺寸/层级/变换并刷新图元。"""
        if self._syncing:
            return

        asset_name = self.asset_combo.currentText().strip()
        if not asset_name:
            return

        item = self._items.get(asset_name)
        if item is None:
            return

        x = self.x_spin.value()
        y = self.y_spin.value()
        w = self.w_spin.value()
        h = self.h_spin.value()
        layer = self.layer_spin.value()
        rotation = self.rotation_spin.value()
        perspective = self.perspective_spin.value()

        self.store.update_asset_geometry(asset_name, x, y, w, h, layer)
        self.store.update_asset_transform(asset_name, rotation, perspective)
        self.layout_changed.emit()
        self._syncing = True
        item.setPos(float(x), float(y))
        item.set_render_size(w, h)
        item.set_visual_transform(rotation, perspective)
        item.setZValue(float(layer))
        self._syncing = False

        self._set_status(f"{asset_name} 参数已更新，记得保存。", success=False)

    def _sync_shop_glass_slider(self) -> None:
        """把商店玻璃透明度同步到滑块；非商店场景禁用该控件。"""
        opacity_percent = int(round(self.store.shop_glass_opacity() * 100))
        enabled = self.scene_combo.currentText().strip() == "shop_screen"
        self._syncing = True
        self.shop_glass_slider.setValue(opacity_percent)
        self.shop_glass_slider.setEnabled(enabled)
        self.shop_glass_value_label.setText(f"{opacity_percent}%")
        self.shop_glass_value_label.setEnabled(enabled)
        self._syncing = False

    def _apply_shop_glass_opacity(self) -> None:
        """商店玻璃透明度滑块变化入口，写入布局 meta。"""
        value = self.shop_glass_slider.value()
        self.shop_glass_value_label.setText(f"{value}%")
        if self._syncing:
            return

        self.store.update_shop_glass_opacity(value / 100)
        self.layout_changed.emit()
        self._set_status(f"商店玻璃不透明度已调整为 {value}%，记得保存。", success=False)

    def _save_layout(self) -> None:
        """保存按钮入口：把内存布局写回 asset_positions.json 并发出变更信号。"""
        self.store.save()
        self.layout_changed.emit()
        self._set_status("坐标已保存到 assets/asset_positions.json", success=True)

    def _set_status(self, text: str, success: bool) -> None:
        """更新底部状态文字和颜色。"""
        color = "#166534" if success else "#9a3412"
        self.status_label.setStyleSheet(f"font-size: 12px; color: {color};")
        self.status_label.setText(text)


def _safe_int(value: Any, default: int) -> int:
    """把 JSON 值安全转成 int，无法转换时使用默认值。"""
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float) -> float:
    """把 JSON 值安全转成 float，无法转换时使用默认值。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _set_optional_float(target: dict[str, Any], key: str, value: float) -> None:
    """把可选浮点参数写入 JSON；接近零时删除字段以保持文件简洁。"""
    value = float(value)
    if abs(value) < 0.0001:
        target.pop(key, None)
        return

    rounded = round(value, 3)
    if rounded == int(rounded):
        target[key] = int(rounded)
    else:
        target[key] = rounded


def asset_visual_transform(width: int, height: int, rotation: float, perspective: float) -> QTransform:
    """根据旋转和上下压平角度生成素材视觉变换，供编辑器和场景共用。"""
    target_w = max(1.0, float(width))
    target_h = max(1.0, float(height))
    clamped_perspective = max(
        -MAX_PERSPECTIVE_DEGREES,
        min(MAX_PERSPECTIVE_DEGREES, float(perspective)),
    )

    transform = QTransform()
    if abs(clamped_perspective) >= 0.0001:
        compression = math.sin(math.radians(abs(clamped_perspective))) * 0.48
        inset = target_w * compression * 0.5
        vertical_shift = target_h * compression * 0.42
        if clamped_perspective > 0:
            destination = QPolygonF(
                [
                    QPointF(inset, vertical_shift),
                    QPointF(target_w - inset, vertical_shift),
                    QPointF(target_w, target_h),
                    QPointF(0.0, target_h),
                ]
            )
        else:
            destination = QPolygonF(
                [
                    QPointF(0.0, 0.0),
                    QPointF(target_w, 0.0),
                    QPointF(target_w - inset, target_h - vertical_shift),
                    QPointF(inset, target_h - vertical_shift),
                ]
            )
        source = QPolygonF(
            [
                QPointF(0.0, 0.0),
                QPointF(target_w, 0.0),
                QPointF(target_w, target_h),
                QPointF(0.0, target_h),
            ]
        )
        transform = QTransform.quadToQuad(source, destination)

    if abs(rotation) >= 0.0001:
        center = QPointF(target_w / 2.0, target_h / 2.0)
        rotation_transform = QTransform()
        rotation_transform.translate(center.x(), center.y())
        rotation_transform.rotate(float(rotation))
        rotation_transform.translate(-center.x(), -center.y())
        transform = transform * rotation_transform

    return transform
