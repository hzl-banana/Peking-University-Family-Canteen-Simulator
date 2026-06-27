"""各个工作台场景的图形 overlay 绘制。

这里根据 `WorkbenchPage` 暴露的状态绘制肠粉、烤盘、烧烤、主食的动态图层。
所有业务修改仍在 `qt_workbench_*.py` mixin；本文件只读状态并通过图元
`data` 字段把点击接口交给 `qt_click_router.py`。
"""

from __future__ import annotations

import math
import time
from typing import Any

from PySide6.QtCore import QRectF, Qt

from pku_simulator.core.catalog import CATALOG, SHOP_LIST
from pku_simulator.core.config import CANVAS_HEIGHT, CANVAS_WIDTH
from pku_simulator.qt_defs import *
from pku_simulator.qt_pages import WorkbenchPage
from pku_simulator.qt_scene import GameSceneView


class WorkbenchOverlayMixin:
    """负责工作台动态图层、信息面板、进度条和可点击区域。"""

    def _render_cheung_fun_overlay(self, view: GameSceneView) -> None:
        """绘制肠粉台：烤台热区、面糊/成品/损坏素材、信息面板和面糊勺。"""
        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            return

        for index in range(len(CHEUNG_FUN_PAN_RECTS)):
            if index >= len(workbench.cheung_fun_pans):
                continue
            rect = CHEUNG_FUN_PAN_RECTS[index]
            pan_data = f"cheung_fun_pan:{index}"
            view.add_rect_item(
                int(rect.x()),
                int(rect.y()),
                int(rect.width()),
                int(rect.height()),
                fill="transparent",
                outline="transparent",
                layer=190,
                data=pan_data,
            )

            pan = workbench._cheung_fun_pan_state(index)
            if bool(pan.get("exploded", False)):
                damaged_asset_name = CHEUNG_FUN_DAMAGED_ASSET_NAMES[index]
                image_x, image_y, image_w, image_h, image_layer = view.store.asset_geometry(damaged_asset_name)
                damaged_item = view.add_asset_item(
                    damaged_asset_name,
                    image_x,
                    image_y,
                    image_w,
                    image_h,
                    layer=image_layer,
                    data=pan_data,
                )
                if damaged_item is not None:
                    damaged_item.setCursor(Qt.PointingHandCursor)
                continue

            if bool(pan.get("has_batter", False)):
                ingredient_entries = workbench._cheung_fun_ingredient_entries(pan)
                asset_name = self._cheung_fun_asset_name_for_pan(index, pan, ingredient_entries)
                image_x, image_y, image_w, image_h, image_layer = view.store.asset_geometry(asset_name)
                item = view.add_asset_item(
                    asset_name,
                    image_x,
                    image_y,
                    image_w,
                    image_h,
                    layer=image_layer,
                    data=pan_data,
                )
                if item is not None:
                    item.setCursor(Qt.PointingHandCursor)

                if index in workbench.visible_cheung_fun_info_pans:
                    self._render_cheung_fun_info_box(
                        view,
                        index,
                        rect,
                        ingredient_entries,
                        bool(pan.get("finished", False)),
                    )

        spoon_asset_name = (
            CHEUNG_FUN_FILLED_SPOON_ASSET_NAME
            if workbench.cheung_fun_spoon_filled
            else CHEUNG_FUN_EMPTY_SPOON_ASSET_NAME
        )
        spoon_state = "filled" if workbench.cheung_fun_spoon_filled else "empty"
        x, y, w, h, layer = view.store.asset_geometry(CHEUNG_FUN_EMPTY_SPOON_ASSET_NAME)
        spoon_item = view.add_asset_item(
            spoon_asset_name,
            x,
            y,
            w,
            h,
            layer=max(130, layer),
            data=f"cheung_fun_spoon:{spoon_state}",
        )
        if spoon_item is not None:
            spoon_item.setCursor(Qt.OpenHandCursor)


    def _cheung_fun_asset_name_for_pan(
        self,
        pan_index: int,
        pan: dict[str, Any],
        ingredient_entries: list[dict[str, Any]],
    ) -> str:
        """根据烤台位置、配料组合和完成状态选择对应肠粉素材。"""
        if bool(pan.get("finished", False)):
            if 0 <= pan_index < len(CHEUNG_FUN_FINISHED_ASSET_NAMES):
                return CHEUNG_FUN_FINISHED_ASSET_NAMES[pan_index]
            return CHEUNG_FUN_FINISHED_ASSET_NAME

        ingredient_set = frozenset(
            str(entry["key"])
            for entry in ingredient_entries
            if str(entry.get("key", "")) in {"egg", "shrimp"}
        )
        if pan_index in {0, 2}:
            asset_pair = CHEUNG_FUN_LEFT_ASSET_NAMES_BY_INGREDIENTS.get(
                ingredient_set,
                CHEUNG_FUN_LEFT_ASSET_NAMES_BY_INGREDIENTS[frozenset()],
            )
            return asset_pair[0 if pan_index == 0 else 1]

        asset_pair = CHEUNG_FUN_RIGHT_ASSET_NAMES_BY_INGREDIENTS.get(
            ingredient_set,
            CHEUNG_FUN_RIGHT_ASSET_NAMES_BY_INGREDIENTS[frozenset()],
        )
        return asset_pair[0 if pan_index == 1 else 1]


    def _render_cheung_fun_info_box(
        self,
        view: GameSceneView,
        pan_index: int,
        pan_rect: QRectF,
        ingredient_entries: list[dict[str, Any]],
        finished: bool,
    ) -> None:
        """绘制肠粉状态面板，展示面糊/配料熟度并暴露 `cheung_fun_out:{i}`。"""
        row_count = max(1, len(ingredient_entries))
        box_w = 2080
        row_h = 210
        footer_h = 290
        box_h = 360 + row_count * row_h + footer_h
        box_x = int(pan_rect.center().x() - box_w / 2)
        box_y = int(pan_rect.y() - box_h + 70)
        box_x = max(40, min(box_x, int(view.graphics_scene.sceneRect().width()) - box_w - 40))
        box_y = max(40, min(box_y, int(view.graphics_scene.sceneRect().height()) - box_h - 40))
        panel_data = f"cheung_fun_info:{pan_index}"

        view.add_rounded_rect_item(
            box_x + 34,
            box_y + 46,
            box_w,
            box_h,
            radius=120,
            fill="#55000000",
            layer=258,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            box_x,
            box_y,
            box_w,
            box_h,
            radius=120,
            fill="#EAF8FBFF",
            outline="#F8FFFFFF",
            layer=260,
            outline_width=7,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            box_x + 34,
            box_y + 34,
            box_w - 68,
            128,
            radius=64,
            fill="#88FFFFFF",
            outline="#33FFFFFF",
            layer=261,
            data=panel_data,
        )
        now = time.monotonic()
        started_at = None
        workbench = self._pages.get("workbench")
        if isinstance(workbench, WorkbenchPage) and 0 <= pan_index < len(workbench.cheung_fun_pans):
            started_at = workbench._cheung_fun_pan_state(pan_index).get("started_at")
        try:
            batter_elapsed = max(0.0, now - float(started_at))
        except (TypeError, ValueError):
            batter_elapsed = 0.0
        batter_cooked = batter_elapsed >= CHEUNG_FUN_BATTER_COOK_SECONDS
        exploded = any(
            now - float(entry["added_at"]) > CHEUNG_FUN_OVERCOOK_SECONDS
            for entry in ingredient_entries
        )
        all_cooked = all(
            now - float(entry["added_at"]) >= _griddle_cook_seconds_for_key(str(entry["key"]))
            for entry in ingredient_entries
        ) and batter_cooked
        if not ingredient_entries:
            state_text = "可出锅" if finished else "熟了" if batter_cooked else "没熟"
        else:
            state_text = "爆炸" if exploded else "可出锅" if finished else "熟了" if all_cooked else "没熟"

        view.add_text_item(
            f"肠粉状态：{state_text}",
            box_x,
            box_y + 48,
            88,
            color="#0f172a",
            layer=270,
            bold=True,
            width=box_w,
            align_center=True,
            data=panel_data,
        )

        row_y = box_y + 200
        if ingredient_entries:
            self._render_cheung_fun_batter_row(view, batter_elapsed, box_x, row_y, box_w, panel_data)
            for row, entry in enumerate(ingredient_entries):
                self._render_cheung_fun_progress_row(
                    view,
                    str(entry["key"]),
                    max(0.0, now - float(entry["added_at"])),
                    box_x,
                    row_y + (row + 1) * row_h,
                    box_w,
                    panel_data,
                )
        else:
            self._render_cheung_fun_batter_row(view, batter_elapsed, box_x, row_y, box_w, panel_data)

        out_enabled = finished and not exploded
        out_data = f"cheung_fun_out:{pan_index}" if out_enabled else None
        out_button_x = box_x + 500
        out_button_y = box_y + box_h - footer_h + 48
        out_button_w = box_w - 1000
        out_button_h = 192
        view.add_rounded_rect_item(
            out_button_x,
            out_button_y,
            out_button_w,
            out_button_h,
            radius=96,
            fill="#E6B91C1C" if out_enabled else "#E4CBD5E1",
            outline="#F8FFFFFF",
            layer=890,
            data=out_data,
            outline_width=5,
        )
        if out_enabled:
            view.add_rect_item(
                out_button_x,
                out_button_y,
                out_button_w,
                out_button_h,
                fill="#01ffffff",
                outline="#01ffffff",
                layer=900,
                data=out_data,
            )
        view.add_text_item(
            "出锅",
            box_x,
            out_button_y + 24,
            108,
            color="#ffffff" if out_enabled else "#64748b",
            layer=910,
            data=out_data,
            bold=True,
            width=box_w,
            align_center=True,
        )


    def _render_cheung_fun_info_row(
        self,
        view: GameSceneView,
        text: str,
        box_x: int,
        row_y: int,
        box_w: int,
        panel_data: str,
    ) -> None:
        """绘制肠粉信息面板中的普通文本行。"""
        row_w = 1320
        row_h = 118
        row_x = int(box_x + (box_w - row_w) / 2)
        view.add_rounded_rect_item(
            row_x,
            row_y,
            row_w,
            row_h,
            radius=59,
            fill="#A8FFFFFF",
            outline="#66FFFFFF",
            layer=268,
            data=panel_data,
            outline_width=4,
        )
        view.add_text_item(
            text,
            row_x,
            row_y + 18,
            70,
            color="#0f172a",
            layer=272,
            width=row_w,
            align_center=True,
            data=panel_data,
        )


    def _render_cheung_fun_batter_row(
        self,
        view: GameSceneView,
        batter_elapsed: float,
        box_x: int,
        row_y: int,
        box_w: int,
        panel_data: str,
    ) -> None:
        """绘制面糊进度行；面糊只判断熟度，不触发爆炸过熟段。"""
        self._render_cheung_fun_progress_row(
            view,
            "rice_batter",
            batter_elapsed,
            box_x,
            row_y,
            box_w,
            panel_data,
            cook_seconds=CHEUNG_FUN_BATTER_COOK_SECONDS,
            overcook_enabled=False,
        )


    def _render_cheung_fun_progress_row(
        self,
        view: GameSceneView,
        item_key: str,
        item_elapsed: float,
        box_x: int,
        row_y: int,
        box_w: int,
        panel_data: str,
        cook_seconds: float | None = None,
        overcook_enabled: bool = True,
    ) -> None:
        """绘制肠粉配料熟度条，并用红色段提示即将/已经爆炸。"""
        ingredient = CATALOG.get(item_key)
        ingredient_name = ingredient.name if ingredient is not None else item_key
        cook_seconds = cook_seconds if cook_seconds is not None else _griddle_cook_seconds_for_key(item_key)
        raw_ratio = _clamped_ratio(item_elapsed / cook_seconds)
        overcook_ratio = 0.0
        if overcook_enabled and item_elapsed >= cook_seconds:
            overcook_ratio = _clamped_ratio(
                (item_elapsed - cook_seconds) / (CHEUNG_FUN_OVERCOOK_SECONDS - cook_seconds)
            )
        exploded = overcook_enabled and item_elapsed > CHEUNG_FUN_OVERCOOK_SECONDS
        status = "爆炸" if exploded else "熟了" if item_elapsed >= cook_seconds else "没熟"
        status_color = "#991b1b" if exploded else "#166534" if item_elapsed >= cook_seconds else "#475569"

        name_w = 420
        status_w = 220
        bar_w = 1000
        bar_h = 68
        gap = 58
        total_w = name_w + gap + bar_w + gap + status_w
        start_x = int(box_x + (box_w - total_w) / 2)
        row_center_y = row_y + 104
        text_y = row_center_y - 62
        bar_x = start_x + name_w + gap
        bar_y = row_center_y - bar_h // 2 - 15

        view.add_text_item(
            ingredient_name,
            start_x,
            text_y,
            70,
            color="#0f172a",
            layer=280,
            width=name_w,
            align_center=True,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            bar_x,
            bar_y,
            bar_w,
            bar_h,
            radius=34,
            fill="#D8FFFFFF",
            outline="#88FFFFFF",
            layer=275,
            data=panel_data,
            outline_width=6,
        )
        if raw_ratio > 0:
            view.add_rounded_rect_item(
                bar_x,
                bar_y,
                int(round(bar_w * raw_ratio)),
                bar_h,
                radius=34,
                fill="#88D1D5DB",
                outline="transparent",
                layer=276,
                data=panel_data,
            )
        if overcook_ratio > 0:
            view.add_rounded_rect_item(
                bar_x,
                bar_y,
                int(round(bar_w * overcook_ratio)),
                bar_h,
                radius=34,
                fill="#A6F87171",
                outline="transparent",
                layer=277,
                data=panel_data,
            )
        view.add_text_item(
            status,
            bar_x + bar_w + gap,
            text_y,
            70,
            color=status_color,
            layer=280,
            width=status_w,
            align_center=True,
            data=panel_data,
        )


    def _render_griddle_overlay(self, view: GameSceneView) -> None:
        """绘制煎扒烤盘：热区、锅盖、损坏素材和烹饪信息面板。"""
        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            return

        for index in range(len(GRIDDLE_PAN_RECTS)):
            rect = view.griddle_pan_rect(index)
            pan = workbench.griddle_pans[index]
            x = int(rect.x())
            y = int(rect.y())
            elapsed = workbench.griddle_pan_elapsed(index)
            ingredients = workbench._griddle_ingredient_entries(pan)
            pan_data = f"griddle_pan:{index}"

            view.add_rect_item(
                x,
                y,
                int(rect.width()),
                int(rect.height()),
                fill="transparent",
                outline="transparent",
                layer=190,
                data=pan_data,
            )

            if bool(pan.get("broken", False)):
                damaged_asset_name = GRIDDLE_DAMAGED_ASSET_NAMES[index]
                damaged_x, damaged_y, damaged_w, damaged_h, _damaged_layer = view.store.asset_geometry(damaged_asset_name)
                view.add_asset_item(
                    damaged_asset_name,
                    damaged_x,
                    damaged_y,
                    damaged_w,
                    damaged_h,
                    layer=170,
                    data=pan_data,
                )
                continue

            if ingredients:
                lid_asset_name = GRIDDLE_LID_ASSET_NAMES[index]
                lid_x, lid_y, lid_w, lid_h, _lid_layer = view.store.asset_geometry(lid_asset_name)
                view.add_asset_item(
                    lid_asset_name,
                    lid_x,
                    lid_y,
                    lid_w,
                    lid_h,
                    layer=170,
                    data=pan_data,
                )

            if index in workbench.visible_griddle_info_pans:
                self._render_griddle_info_box(view, index, rect, ingredients, elapsed)


    def _render_griddle_info_box(
        self,
        view: GameSceneView,
        pan_index: int,
        pan_rect: QRectF,
        ingredients: list[dict[str, Any]],
        elapsed: float,
    ) -> None:
        """绘制烤盘信息面板，展示每个食材熟度并暴露 `griddle_out:{i}`。"""
        box_w = 2200
        row_h = 230
        footer_h = 300
        box_h = 310 + max(1, len(ingredients)) * row_h + footer_h
        box_x = int(pan_rect.center().x() - box_w / 2)
        box_y = int(pan_rect.y() - box_h + 70)
        box_x = max(40, min(box_x, int(view.graphics_scene.sceneRect().width()) - box_w - 40))
        box_y = max(40, min(box_y, int(view.graphics_scene.sceneRect().height()) - box_h - 40))
        panel_data = f"griddle_info:{pan_index}"

        view.add_rounded_rect_item(
            box_x + 34,
            box_y + 46,
            box_w,
            box_h,
            radius=120,
            fill="#55000000",
            layer=258,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            box_x,
            box_y,
            box_w,
            box_h,
            radius=120,
            fill="#EAF8FBFF",
            outline="#F8FFFFFF",
            layer=260,
            outline_width=7,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            box_x + 34,
            box_y + 34,
            box_w - 68,
            128,
            radius=64,
            fill="#88FFFFFF",
            outline="#33FFFFFF",
            layer=261,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            box_x + 78,
            box_y + box_h - 126,
            120,
            120,
            radius=60,
            fill="#55FFFFFF",
            outline="#33FFFFFF",
            layer=261,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            box_x + 220,
            box_y + box_h - 72,
            58,
            58,
            radius=29,
            fill="#44FFFFFF",
            outline="#22FFFFFF",
            layer=261,
            data=panel_data,
        )
        view.add_text_item(
            f"总烹饪时长：{elapsed:.1f}s",
            box_x,
            box_y + 48,
            92,
            color="#0f172a",
            layer=270,
            bold=True,
            width=box_w,
            align_center=True,
            data=panel_data,
        )

        if ingredients:
            now = time.monotonic()
            for row, entry in enumerate(ingredients):
                self._render_griddle_progress_row(
                    view,
                    str(entry["key"]),
                    max(0.0, now - float(entry["added_at"])),
                    elapsed,
                    box_x,
                    box_y + 180 + row * row_h,
                    box_w,
                    panel_data,
                )
        else:
            view.add_text_item(
                "暂无食材",
                box_x,
                box_y + 205,
                84,
                color="#0f172a",
                layer=270,
                width=box_w,
                align_center=True,
                data=panel_data,
            )

        out_y = box_y + box_h - footer_h - 30
        out_data = f"griddle_out:{pan_index}"
        out_button_x = box_x + 500
        out_button_y = out_y + 44
        out_button_w = box_w - 1000
        out_button_h = 192
        view.add_rounded_rect_item(
            out_button_x,
            out_button_y,
            out_button_w,
            out_button_h,
            radius=96,
            fill="#F2FFFFFF",
            outline="#CCFFFFFF",
            layer=890,
            data=out_data,
            outline_width=5,
        )
        view.add_rect_item(
            out_button_x,
            out_button_y,
            out_button_w,
            out_button_h,
            fill="#01ffffff",
            outline="#01ffffff",
            layer=900,
            data=out_data,
        )
        view.add_text_item(
            "出锅",
            box_x,
            out_y + 70,
            108,
            color="#991b1b",
            layer=910,
            data=out_data,
            bold=True,
            width=box_w,
            align_center=True,
        )


    def _render_griddle_progress_row(
        self,
        view: GameSceneView,
        item_key: str,
        item_elapsed: float,
        pan_elapsed: float,
        box_x: int,
        row_y: int,
        box_w: int,
        panel_data: str,
    ) -> None:
        """绘制烤盘食材进度条，结合单个食材时间和整盘过熟时间判断可食用。"""
        ingredient = CATALOG.get(item_key)
        ingredient_name = ingredient.name if ingredient is not None else item_key
        cook_seconds = _griddle_cook_seconds_for_key(item_key)
        raw_ratio = _clamped_ratio(item_elapsed / cook_seconds)
        overcook_ratio = 0.0
        if item_elapsed >= cook_seconds:
            overcook_ratio = _clamped_ratio(
                (pan_elapsed - cook_seconds) / (GRIDDLE_OVERCOOK_SECONDS - cook_seconds)
            )
        is_edible_now = (
            item_elapsed >= cook_seconds
            and pan_elapsed <= GRIDDLE_OVERCOOK_SECONDS
        )
        status = "✅" if is_edible_now else "❌"

        name_w = 460
        status_w = 170
        bar_w = 1050
        bar_h = 68
        gap = 65
        total_w = name_w + gap + bar_w + gap + status_w
        start_x = int(box_x + (box_w - total_w) / 2)
        row_center_y = row_y + 112
        text_y = row_center_y - 62
        bar_x = start_x + name_w + gap
        bar_y = row_center_y - bar_h // 2 - 17

        view.add_text_item(
            ingredient_name,
            start_x,
            text_y,
            76,
            color="#0f172a",
            layer=280,
            width=name_w,
            align_center=True,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            bar_x,
            bar_y,
            bar_w,
            bar_h,
            radius=34,
            fill="#D8FFFFFF",
            outline="#88FFFFFF",
            layer=275,
            data=panel_data,
            outline_width=6,
        )
        if raw_ratio > 0:
            view.add_rounded_rect_item(
                bar_x,
                bar_y,
                int(round(bar_w * raw_ratio)),
                bar_h,
                radius=34,
                fill="#88D1D5DB",
                outline="transparent",
                layer=276,
                data=panel_data,
            )
        if overcook_ratio > 0:
            view.add_rounded_rect_item(
                bar_x,
                bar_y,
                int(round(bar_w * overcook_ratio)),
                bar_h,
                radius=34,
                fill="#A6F87171",
                outline="transparent",
                layer=277,
                data=panel_data,
            )
        view.add_text_item(
            status,
            bar_x + bar_w + gap,
            text_y,
            76,
            color="#0f172a",
            layer=280,
            width=status_w,
            align_center=True,
            data=panel_data,
        )


    def _render_bbq_overlay(self, view: GameSceneView) -> None:
        """绘制烧烤架上的烤串、辣椒标记、烟雾和熟串出串面板。"""
        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            return

        for slot_index in range(len(BBQ_SLOT_ASSET_NAMES)):
            rect = view.bbq_slot_rect(slot_index)
            slot = workbench.bbq_slot_state(slot_index)
            if slot is None:
                continue

            item_key = str(slot.get("key", ""))
            cooked = workbench.bbq_slot_cooked(slot_index)
            asset_name = self._bbq_skewer_asset_name_for_slot(
                view,
                item_key,
                slot_index,
                rect,
                cooked,
            )
            if asset_name is None:
                continue

            image_x, image_y, asset_w, asset_h, asset_layer = self._bbq_skewer_render_geometry(
                view,
                asset_name,
                slot_index,
                rect,
                cooked,
            )
            item = view.add_asset_item(
                asset_name,
                image_x,
                image_y,
                asset_w,
                asset_h,
                layer=asset_layer,
                data=f"bbq_slot:{slot_index}",
            )
            if item is not None and cooked:
                item.setCursor(Qt.PointingHandCursor)

            if bool(slot.get("has_chili", False)):
                badge_w = max(56, int(rect.width() * 0.20))
                badge_h = max(48, int(rect.height() * 0.14))
                badge_x = int(rect.x() + rect.width() * 0.08)
                badge_y = int(rect.y() + rect.height() * 0.08)
                view.add_rounded_rect_item(
                    badge_x,
                    badge_y,
                    badge_w,
                    badge_h,
                    radius=max(20, badge_h // 2),
                    fill="#DDB91C1C",
                    outline="#FFFEE2E2",
                    layer=asset_layer + 8,
                    outline_width=4,
                )
                view.add_text_item(
                    "辣",
                    badge_x,
                    badge_y + 2,
                    max(30, int(badge_h * 0.62)),
                    color="#ffffff",
                    layer=asset_layer + 9,
                    bold=True,
                    width=badge_w,
                    align_center=True,
                )

            self._render_bbq_smoke(view, slot_index, rect)

            if cooked and slot_index in workbench.visible_bbq_info_slots:
                self._render_bbq_done_box(view, slot_index, rect)


    def _render_bbq_smoke(
        self,
        view: GameSceneView,
        slot_index: int,
        slot_rect: QRectF,
    ) -> None:
        """按槽位和时间生成轻量烟雾粒子，纯视觉效果，不参与业务状态。"""
        now = time.monotonic()
        center = slot_rect.center()
        center_x = center.x()
        slot_w = slot_rect.width()
        slot_h = slot_rect.height()
        origin_y = slot_rect.y() + slot_h * 0.38
        rise_h = slot_h * 0.84
        seed = slot_index * 19.37 + 7.0

        # 先铺一层淡烟体积，再叠加上升粒子，避免烟雾显得太单薄。
        for haze_index in range(3):
            haze_phase = (now * 0.06 + slot_index * 0.17 + haze_index * 0.29) % 1.0
            haze_lift = rise_h * (0.12 + haze_phase * 0.16)
            haze_w = max(28, int(slot_w * (0.46 + haze_phase * 0.26)))
            haze_h = max(18, int(slot_h * (0.10 + haze_phase * 0.05)))
            haze_x = center_x + math.sin(seed + haze_index * 2.7 + now * 0.23) * slot_w * 0.05
            haze_y = origin_y - haze_lift
            view.add_ellipse_item(
                int(haze_x - haze_w / 2),
                int(haze_y - haze_h / 2),
                haze_w,
                haze_h,
                fill=_alpha_color("#FFFFFF", 0.05 + haze_phase * 0.05),
                layer=BBQ_SMOKE_LAYER + haze_index,
            )

        for particle_index in range(BBQ_SMOKE_PARTICLE_COUNT):
            phase = (
                now * (0.18 + 0.018 * ((particle_index + slot_index) % 5))
                + slot_index * 0.113
                + particle_index / BBQ_SMOKE_PARTICLE_COUNT
            ) % 1.0
            ease = 1.0 - (1.0 - phase) ** 2
            fade_in = _clamped_ratio(phase / 0.18)
            fade_out = _clamped_ratio((1.0 - phase) / 0.56)
            opacity = 0.34 * fade_in * fade_out * (1.0 - phase * 0.36)
            if opacity <= 0.012:
                continue

            drift_seed = seed + particle_index * 2.417
            birth_offset = (
                math.sin(drift_seed * 1.7) * 0.26
                + math.sin(drift_seed * 0.73) * 0.12
            ) * slot_w
            wind = math.sin(now * 0.48 + drift_seed) * slot_w * (0.07 + 0.20 * phase)
            curl = math.sin(now * 1.1 + drift_seed * 1.31 + phase * math.tau) * slot_w * 0.08
            x = center_x + birth_offset * (1.0 - phase * 0.42) + wind + curl
            y = origin_y - rise_h * ease - math.sin(drift_seed + phase * math.pi) * slot_h * 0.035

            base_w = max(18, int(slot_w * (0.09 + 0.03 * (particle_index % 4))))
            base_h = max(12, int(slot_h * (0.05 + 0.012 * (particle_index % 3))))
            growth = 1.0 + phase * (1.8 + 0.42 * math.sin(drift_seed))
            puff_w = max(16, int(base_w * growth))
            puff_h = max(12, int(base_h * (1.0 + phase * 1.5)))
            x += math.sin(drift_seed * 0.41 + phase * math.tau) * puff_w * 0.16

            layer_specs = (
                (1.95, 1.48, opacity * 0.10, 0.20, 0),
                (1.32, 1.10, opacity * 0.20, 0.10, 1),
                (0.90, 0.76, opacity * 0.36, 0.02, 2),
                (0.50, 0.42, opacity * 0.56, -0.04, 3),
            )
            for scale_w, scale_h, layer_opacity, y_lift_factor, layer_offset in layer_specs:
                item_w = max(10, int(puff_w * scale_w))
                item_h = max(8, int(puff_h * scale_h))
                wobble_x = math.sin(
                    drift_seed * 0.41 + phase * math.tau + layer_offset * 0.7
                ) * item_w * (0.03 + 0.02 * layer_offset)
                wobble_y = math.cos(
                    drift_seed * 0.35 + phase * math.tau + layer_offset * 0.5
                ) * slot_h * 0.01
                view.add_ellipse_item(
                    int(x + wobble_x - item_w / 2),
                    int(y - item_h / 2 - slot_h * y_lift_factor + wobble_y),
                    item_w,
                    item_h,
                    fill=_alpha_color("#FFFFFF", layer_opacity),
                    layer=BBQ_SMOKE_LAYER + 3 + layer_offset,
                )


    def _bbq_skewer_asset_name_for_slot(
        self,
        view: GameSceneView,
        item_key: str,
        slot_index: int,
        slot_rect: QRectF,
        cooked: bool,
    ) -> str | None:
        """根据槽位左右位置和熟度选择对应的烤串素材。"""
        group = self._bbq_slot_position_group(view, slot_index, slot_rect)
        if cooked and group == "middle":
            return BBQ_MIDDLE_COOKED_SKEWER_ASSET_NAMES_BY_KEY.get(item_key)
        if cooked and group == "right":
            return BBQ_RIGHT_COOKED_SKEWER_ASSET_NAMES_BY_KEY.get(item_key)
        if cooked:
            return BBQ_LEFT_COOKED_SKEWER_ASSET_NAMES_BY_KEY.get(item_key)
        if group == "middle":
            return BBQ_MIDDLE_COOKING_SKEWER_ASSET_NAMES_BY_KEY.get(item_key)
        if group == "right":
            return BBQ_RIGHT_COOKING_SKEWER_ASSET_NAMES_BY_KEY.get(item_key)
        return BBQ_LEFT_COOKING_SKEWER_ASSET_NAMES_BY_KEY.get(item_key)


    def _bbq_slot_position_group(
        self,
        view: GameSceneView,
        slot_index: int,
        slot_rect: QRectF,
    ) -> str:
        """把烧烤槽位按横向排序归到 left/middle/right，匹配透视素材。"""
        del slot_rect
        slot_count = len(BBQ_SLOT_ASSET_NAMES)
        if not 0 <= slot_index < slot_count:
            return "middle"

        ordered_indexes = sorted(
            range(slot_count),
            key=lambda index: (
                view.bbq_slot_rect(index).center().x(),
                view.bbq_slot_rect(index).center().y(),
                index,
            ),
        )
        try:
            rank = ordered_indexes.index(slot_index)
        except ValueError:
            return "middle"

        side_count = max(1, slot_count // 4)
        if rank < side_count:
            return "left"
        if rank >= slot_count - side_count:
            return "right"
        return "middle"


    def _bbq_skewer_render_geometry(
        self,
        view: GameSceneView,
        asset_name: str,
        slot_index: int,
        slot_rect: QRectF,
        cooked: bool,
    ) -> tuple[int, int, int, int, int]:
        """把烤串素材中心对齐到槽位中心，保持 asset layout 中保存的尺寸/层级。"""
        template_x, template_y, template_w, template_h, template_layer = view.store.asset_geometry(asset_name)
        del view, slot_index, cooked
        image_x = round(slot_rect.center().x() - template_w / 2)
        image_y = round(slot_rect.center().y() - template_h / 2)
        return int(image_x), int(image_y), template_w, template_h, template_layer


    def _render_bbq_done_box(
        self,
        view: GameSceneView,
        slot_index: int,
        slot_rect: QRectF,
    ) -> None:
        """绘制熟串信息面板，`bbq_finish:{i}` 由点击路由转到出串动作。"""
        workbench = self._pages.get("workbench")
        slot = workbench.bbq_slot_state(slot_index) if isinstance(workbench, WorkbenchPage) else None
        has_chili = bool(slot.get("has_chili", False)) if slot is not None else False

        box_w = 940
        box_h = 460
        box_x = int(slot_rect.center().x() - box_w / 2)
        box_y = int(slot_rect.y() - box_h + 80)
        box_x = max(40, min(box_x, int(view.graphics_scene.sceneRect().width()) - box_w - 40))
        box_y = max(40, min(box_y, int(view.graphics_scene.sceneRect().height()) - box_h - 40))
        finish_data = f"bbq_finish:{slot_index}"
        seasoning_label = "调味: 孜然 + 辣椒" if has_chili else "调味: 孜然"

        view.add_rounded_rect_item(
            box_x + 22,
            box_y + 30,
            box_w,
            box_h,
            radius=96,
            fill="#55000000",
            layer=885,
            data=f"bbq_info:{slot_index}",
        )
        view.add_rounded_rect_item(
            box_x,
            box_y,
            box_w,
            box_h,
            radius=96,
            fill="#EAF8FBFF",
            outline="#F8FFFFFF",
            layer=890,
            outline_width=6,
            data=f"bbq_info:{slot_index}",
        )
        view.add_rounded_rect_item(
            box_x + 90,
            box_y + 286,
            box_w - 180,
            134,
            radius=67,
            fill="#DDB91C1C",
            outline="#FFFEE2E2",
            layer=900,
            outline_width=5,
            data=finish_data,
        )
        view.add_text_item(
            "烤好了",
            box_x,
            box_y + 82,
            92,
            color="#0f172a",
            layer=910,
            bold=True,
            width=box_w,
            align_center=True,
            data=f"bbq_info:{slot_index}",
        )
        view.add_text_item(
            seasoning_label,
            box_x,
            box_y + 210,
            58,
            color="#334155",
            layer=910,
            width=box_w,
            align_center=True,
            data=f"bbq_info:{slot_index}",
        )
        view.add_text_item(
            "出串",
            box_x + 90,
            box_y + 318,
            62,
            color="#ffffff",
            layer=910,
            bold=True,
            width=box_w - 180,
            align_center=True,
            data=finish_data,
        )


    def _render_staple_overlay(self, view: GameSceneView) -> None:
        """绘制主食台：米水来源、电饭煲状态素材和电饭煲操作面板。"""
        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            return

        workbench.update_staple_cookers()

        background_asset = (
            STAPLE_FILLED_BACKGROUND_ASSET_NAME
            if self.service.get_quantity("rice") > 0
            else STAPLE_EMPTY_BACKGROUND_ASSET_NAME
        )
        view.add_asset_item(background_asset, 0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, layer=0)

        for source_asset_name, item_key in STAPLE_SOURCE_ASSET_KEYS.items():
            if self.service.get_quantity(item_key) <= 0:
                continue
            x, y, w, h, layer = view.store.asset_geometry(source_asset_name)
            source = view.add_asset_item(
                source_asset_name,
                x,
                y,
                w,
                h,
                layer=layer,
                data=f"staple_ingredient:{item_key}:{source_asset_name}",
            )
            if source is not None:
                source.setCursor(Qt.OpenHandCursor)

        for index in range(len(STAPLE_COOKER_SLOT_ASSET_NAMES)):
            state_name = workbench.staple_cooker_state_name(index)
            asset_name = STAPLE_COOKER_ASSET_NAMES_BY_STATE.get(
                state_name,
                STAPLE_COOKER_ASSET_NAMES_BY_STATE["empty"],
            )
            x, y, w, h, layer = self._staple_cooker_render_geometry(
                view,
                asset_name,
                index,
            )
            cooker_item = view.add_asset_item(
                asset_name,
                x,
                y,
                w,
                h,
                layer=layer,
                data=f"staple_cooker:{index}",
            )
            if cooker_item is not None:
                cooker_item.setCursor(Qt.PointingHandCursor)

            if index in workbench.visible_staple_info_cookers:
                self._render_staple_info_box(
                    view,
                    index,
                    QRectF(float(x), float(y), float(w), float(h)),
                    state_name,
                )


    def _staple_cooker_render_geometry(
        self,
        view: GameSceneView,
        asset_name: str,
        cooker_index: int,
    ) -> tuple[int, int, int, int, int]:
        """把非空电饭煲素材对齐到对应槽位，保留第一槽位作为模板锚点。"""
        slot_name = STAPLE_COOKER_SLOT_ASSET_NAMES[cooker_index]
        slot_x, slot_y, slot_w, slot_h, slot_layer = view.store.asset_geometry(slot_name)
        empty_asset_name = STAPLE_COOKER_ASSET_NAMES_BY_STATE["empty"]
        if asset_name == empty_asset_name or not view.store.asset_metadata(asset_name):
            return slot_x, slot_y, slot_w, slot_h, slot_layer

        template_x, template_y, template_w, template_h, template_layer = view.store.asset_geometry(asset_name)
        anchor_slot_x, anchor_slot_y, anchor_slot_w, anchor_slot_h, _anchor_slot_layer = view.store.asset_geometry(
            STAPLE_COOKER_SLOT_ASSET_NAMES[0]
        )
        template_center_x = template_x + template_w / 2
        template_center_y = template_y + template_h / 2
        anchor_center_x = anchor_slot_x + anchor_slot_w / 2
        anchor_center_y = anchor_slot_y + anchor_slot_h / 2
        slot_center_x = slot_x + slot_w / 2
        slot_center_y = slot_y + slot_h / 2

        x = round(slot_center_x + (template_center_x - anchor_center_x) - template_w / 2)
        y = round(slot_center_y + (template_center_y - anchor_center_y) - template_h / 2)
        layer = template_layer + (60 if cooker_index >= 3 else 0)
        return int(x), int(y), template_w, template_h, layer


    def _render_staple_info_box(
        self,
        view: GameSceneView,
        cooker_index: int,
        cooker_rect: QRectF,
        state_name: str,
    ) -> None:
        """绘制电饭煲状态面板，并暴露 `staple_start/finish:{i}` 点击接口。"""
        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            return

        cooker = workbench._staple_cooker_state(cooker_index)
        has_rice = bool(cooker.get("has_rice", False))
        has_water = bool(cooker.get("has_water", False))
        is_cooking = state_name == "cooking"
        is_done = state_name == "done"
        can_start = state_name == "ready"
        can_finish = is_done

        box_w = 1120
        box_h = 620
        box_x = int(cooker_rect.center().x() - box_w / 2)
        box_y = int(cooker_rect.y() - box_h + cooker_rect.height() * 0.22)
        scene_rect = view.graphics_scene.sceneRect()
        box_x = max(40, min(box_x, int(scene_rect.width()) - box_w - 40))
        box_y = max(40, min(box_y, int(scene_rect.height()) - box_h - 40))
        panel_data = f"staple_info:{cooker_index}"

        view.add_rounded_rect_item(
            box_x + 24,
            box_y + 30,
            box_w,
            box_h,
            radius=92,
            fill="#52000000",
            layer=885,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            box_x,
            box_y,
            box_w,
            box_h,
            radius=92,
            fill="#EAF8FBFF",
            outline="#F8FFFFFF",
            layer=890,
            outline_width=6,
            data=panel_data,
        )

        content_parts = []
        if has_rice:
            content_parts.append("米")
        if has_water:
            content_parts.append("水")
        content_text = "、".join(content_parts) if content_parts else "空"
        status_text = "蒸饭完成" if is_done else "正在蒸饭" if is_cooking else "等待蒸饭"

        view.add_text_item(
            f"电饭煲 {cooker_index + 1}",
            box_x,
            box_y + 54,
            82,
            color="#7f1d1d",
            layer=900,
            bold=True,
            width=box_w,
            align_center=True,
            data=panel_data,
        )
        view.add_text_item(
            f"内容：{content_text}    状态：{status_text}",
            box_x + 80,
            box_y + 170,
            58,
            color="#0f172a",
            layer=900,
            width=box_w - 160,
            align_center=True,
            data=panel_data,
        )

        progress = 1.0 if is_done else 0.0
        if is_cooking:
            progress = min(1.0, workbench.staple_cooker_elapsed(cooker_index) / STAPLE_RICE_COOK_SECONDS)
        bar_x = box_x + 130
        bar_y = box_y + 270
        bar_w = box_w - 260
        bar_h = 56
        view.add_rounded_rect_item(
            bar_x,
            bar_y,
            bar_w,
            bar_h,
            radius=28,
            fill="#D8FFFFFF",
            outline="#88FFFFFF",
            layer=900,
            outline_width=5,
            data=panel_data,
        )
        if progress > 0:
            view.add_rounded_rect_item(
                bar_x,
                bar_y,
                max(1, int(bar_w * progress)),
                bar_h,
                radius=28,
                fill="#B634D399" if not is_done else "#C022C55E",
                outline="transparent",
                layer=901,
                data=panel_data,
            )

        start_data = f"staple_start:{cooker_index}" if can_start else panel_data
        finish_data = f"staple_finish:{cooker_index}" if can_finish else panel_data
        self._render_staple_button(
            view,
            box_x + 120,
            box_y + 400,
            390,
            "开始蒸饭",
            "#dc2626" if can_start else "#94a3b8",
            start_data,
        )
        self._render_staple_button(
            view,
            box_x + box_w - 510,
            box_y + 400,
            390,
            "出锅",
            "#dc2626" if can_finish else "#94a3b8",
            finish_data,
        )


    def _render_staple_button(
        self,
        view: GameSceneView,
        x: int,
        y: int,
        width: int,
        text: str,
        fill: str,
        data: str,
    ) -> None:
        """绘制主食台信息面板中的按钮。"""
        view.add_rounded_rect_item(
            x,
            y,
            width,
            130,
            radius=56,
            fill=fill,
            outline="#F8FFFFFF",
            layer=905,
            outline_width=4,
            data=data,
        )
        view.add_text_item(
            text,
            x,
            y + 25,
            64,
            color="#ffffff",
            layer=906,
            bold=True,
            width=width,
            align_center=True,
            data=data,
        )


    def _render_staple_progress(
        self,
        view: GameSceneView,
        cooker_index: int,
        cooker_rect: QRectF,
    ) -> None:
        """绘制贴在电饭煲上的小进度条；当前主要由信息面板进度条承担展示。"""
        workbench = self._pages.get("workbench")
        if not isinstance(workbench, WorkbenchPage):
            return

        ratio = min(1.0, workbench.staple_cooker_elapsed(cooker_index) / STAPLE_RICE_COOK_SECONDS)
        bar_w = int(cooker_rect.width() * 0.58)
        bar_h = 54
        bar_x = int(cooker_rect.center().x() - bar_w / 2)
        bar_y = int(cooker_rect.bottom() - bar_h - cooker_rect.height() * 0.12)

        view.add_rounded_rect_item(
            bar_x,
            bar_y,
            bar_w,
            bar_h,
            radius=27,
            fill="#CFFFFFFF",
            outline="#F2FFFFFF",
            layer=330,
            outline_width=4,
        )
        if ratio > 0:
            view.add_rounded_rect_item(
                bar_x,
                bar_y,
                max(1, int(bar_w * ratio)),
                bar_h,
                radius=27,
                fill="#B634D399",
                outline="transparent",
                layer=331,
            )
