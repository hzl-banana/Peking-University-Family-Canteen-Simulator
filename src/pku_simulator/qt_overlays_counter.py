"""点餐台场景的图形 overlay。

这里只负责绘制顾客、订单小票、接单/点餐完成/出餐按钮和现金提示。
所有可点击元素通过 `data` 字段交给 `qt_click_router.py` 分发，订单状态读取
来自 `CounterControllerMixin` 和 `GameService`。
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


class CounterOverlayMixin:
    """渲染点餐台 UI，并把小票点击区域标记给点击路由。"""

    def _render_counter_overlay(self, view: GameSceneView) -> None:
        """点餐台总入口：同步订单，再依次绘制顾客、小票、桌面和收款提示。"""
        if not any(item.data(0) == "点餐台背景.jpg" for item in view.graphics_scene.items()):
            view.add_asset_item("点餐台背景.jpg", 0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, layer=0)
        self.sync_counter_orders()
        self._render_counter_hanging_bar(view)
        self._render_counter_active_customer(view)
        view.add_asset_item(COUNTER_DESK_ASSET_NAME, 0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, layer=120)
        self._render_counter_cash_events(view)
        self._render_counter_zoomed_ticket(view)


    def _render_counter_hanging_bar(self, view: GameSceneView) -> None:
        """绘制已点餐但未出餐的小票挂条；点击小票会放大检查出餐匹配。"""
        for index, order in enumerate(self._counter_completed_orders()):
            order_id = int(order["order_id"])
            target_x = COUNTER_HANGING_TICKET_START_X + index * (
                COUNTER_HANGING_TICKET_WIDTH + COUNTER_HANGING_TICKET_GAP
            )
            target_y = COUNTER_HANGING_TICKET_Y
            start_time = self._counter_hang_started_at_by_order_id.get(order_id)
            if start_time is not None:
                progress = _ease_out_cubic(
                    (time.monotonic() - start_time) / COUNTER_HANGING_ANIMATION_SECONDS
                )
                start_rect = COUNTER_ORDER_TICKET_RECT
                x = int(_lerp_float(start_rect.x(), target_x, progress))
                y = int(_lerp_float(start_rect.y(), target_y, progress))
                w = int(_lerp_float(start_rect.width(), COUNTER_HANGING_TICKET_WIDTH, progress))
                h = int(_lerp_float(start_rect.height(), COUNTER_HANGING_TICKET_HEIGHT, progress))
                if progress >= 1.0:
                    self._counter_hang_started_at_by_order_id.pop(order_id, None)
            else:
                x = target_x
                y = target_y
                w = COUNTER_HANGING_TICKET_WIDTH
                h = COUNTER_HANGING_TICKET_HEIGHT

            self._render_counter_ticket(
                view,
                order_id,
                int(x),
                int(y),
                int(w),
                int(h),
                layer=70,
                mode="hanging",
                clickable=True,
                max_lines=4,
            )


    def _render_counter_active_customer(self, view: GameSceneView) -> None:
        """绘制当前走到柜台的顾客，以及接单按钮或正在生成的小票。"""
        order_id = self._counter_active_customer_order_id
        if order_id is None:
            return

        order = self.service.get_order_by_id(order_id)
        if order is None:
            self.sync_counter_orders()
            return

        elapsed = time.monotonic() - self._counter_active_customer_started_at
        progress = _ease_out_cubic(elapsed / COUNTER_CUSTOMER_POP_SECONDS)
        rect = COUNTER_CUSTOMER_FINAL_RECT
        customer_y = int(rect.y() + COUNTER_CUSTOMER_POP_DISTANCE * (1.0 - progress))
        asset_name = f"{order['customer_name']}.jpg"
        customer = view.add_asset_item(
            asset_name,
            int(rect.x()),
            customer_y,
            int(rect.width()),
            int(rect.height()),
            layer=80,
            data=f"counter_customer:{order_id}",
        )
        if customer is not None:
            customer.setCursor(Qt.PointingHandCursor)

        if progress < 0.9:
            return

        if self._counter_active_ticket_started_at is None:
            if self._counter_accept_prompt_order_id == order_id:
                self._render_counter_accept_button(view, order_id)
            return

        if self._counter_accept_prompt_order_id == order_id:
            self._render_counter_accept_button(view, order_id)
            return

        self._render_counter_active_ticket(view, order_id)


    def _render_counter_accept_button(self, view: GameSceneView, order_id: int) -> None:
        """绘制“接单”按钮，`counter_accept:{id}` 由点击路由转到接单流程。"""
        data = f"counter_accept:{order_id}"
        x = int(COUNTER_CUSTOMER_FINAL_RECT.right() + 280)
        y = int(COUNTER_CUSTOMER_FINAL_RECT.y() + 650)
        view.add_rounded_rect_item(
            x,
            y,
            880,
            280,
            radius=110,
            fill="#DDB91C1C",
            outline="#FFFEE2E2",
            layer=180,
            data=data,
            outline_width=6,
        )
        view.add_text_item(
            "接单",
            x,
            y + 58,
            102,
            color="#ffffff",
            layer=190,
            bold=True,
            width=880,
            align_center=True,
            data=data,
        )


    def _render_counter_active_ticket(self, view: GameSceneView, order_id: int) -> None:
        """逐行展示当前订单内容，全部显示后出现“点餐完毕”按钮。"""
        if self._counter_active_ticket_started_at is None:
            return
        lines = self._counter_active_ticket_lines or self.service.build_order_lines(order_id)
        started_at = self._counter_active_ticket_started_at or time.monotonic()
        visible_count = min(
            len(lines),
            int(max(0.0, time.monotonic() - started_at) / COUNTER_LINE_REVEAL_SECONDS) + 1,
        )
        self._render_counter_ticket(
            view,
            order_id,
            int(COUNTER_ORDER_TICKET_RECT.x()),
            int(COUNTER_ORDER_TICKET_RECT.y()),
            int(COUNTER_ORDER_TICKET_RECT.width()),
            int(COUNTER_ORDER_TICKET_RECT.height()),
            layer=190,
            mode="active",
            clickable=False,
            lines=lines[:visible_count],
            max_lines=18,
        )

        if visible_count < len(lines):
            return

        data = f"counter_order_done:{order_id}"
        btn_w = 1360
        btn_h = 245
        btn_x = int(COUNTER_ORDER_TICKET_RECT.center().x() - btn_w / 2)
        btn_y = int(COUNTER_ORDER_TICKET_RECT.bottom() - 390)
        view.add_rounded_rect_item(
            btn_x,
            btn_y,
            btn_w,
            btn_h,
            radius=112,
            fill="#DDB91C1C",
            outline="#FFFEE2E2",
            layer=245,
            data=data,
            outline_width=6,
        )
        view.add_text_item(
            "点餐完毕",
            btn_x,
            btn_y + 46,
            90,
            color="#ffffff",
            layer=255,
            bold=True,
            width=btn_w,
            align_center=True,
            data=data,
        )


    def _render_counter_zoomed_ticket(self, view: GameSceneView) -> None:
        """绘制被点击放大的挂单小票，并根据成品匹配结果启用/禁用出餐。"""
        order_id = self._counter_zoomed_order_id
        if order_id is None:
            return
        if self.service.get_order_by_id(order_id) is None:
            self.sync_counter_orders()
            return

        view.add_rect_item(
            0,
            0,
            CANVAS_WIDTH,
            CANVAS_HEIGHT,
            fill="#66000000",
            layer=780,
            data="counter_overlay_close",
        )
        ticket_w = 3820
        ticket_h = 4300
        ticket_x = int((CANVAS_WIDTH - ticket_w) / 2)
        ticket_y = 600
        self._render_counter_ticket(
            view,
            order_id,
            ticket_x,
            ticket_y,
            ticket_w,
            ticket_h,
            layer=800,
            mode="zoomed",
            clickable=False,
            max_lines=26,
        )

        preview = self.service.preview_order_match(order_id)
        can_serve = bool(preview.get("can_serve", False))
        data = f"counter_serve:{order_id}" if can_serve else f"counter_ticket_view:{order_id}"
        btn_w = 1500
        btn_h = 260
        btn_x = int((CANVAS_WIDTH - btn_w) / 2)
        btn_y = ticket_y + ticket_h - 405
        view.add_rounded_rect_item(
            btn_x,
            btn_y,
            btn_w,
            btn_h,
            radius=120,
            fill="#DDB91C1C" if can_serve else "#D4CBD5E1",
            outline="#FFFEE2E2",
            layer=860,
            data=data,
            outline_width=6,
        )
        view.add_text_item(
            "出餐",
            btn_x,
            btn_y + 52,
            92,
            color="#ffffff" if can_serve else "#64748b",
            layer=870,
            bold=True,
            width=btn_w,
            align_center=True,
            data=data,
        )


    def _render_counter_ticket(
        self,
        view: GameSceneView,
        order_id: int,
        x: int,
        y: int,
        width: int,
        height: int,
        layer: int,
        mode: str,
        clickable: bool,
        lines: list[str] | None = None,
        max_lines: int = 12,
    ) -> None:
        """绘制小票内容；mode 控制挂条/当前订单/放大态三种排版。"""
        order = self.service.get_order_by_id(order_id)
        if order is None:
            return

        data = f"counter_ticket:{order_id}" if clickable else f"counter_ticket_view:{order_id}"
        self._render_counter_ticket_paper(view, x, y, width, height, layer, mode, data)

        remaining = self.service.get_order_remaining_seconds(order_id)
        compact = mode == "hanging"
        title_size = max(24, int(width * (0.052 if compact else 0.031)))
        body_size = max(21, int(width * (0.036 if compact else 0.0215)))
        pad_x = max(36, int(width * (0.09 if compact else 0.105)))
        title_y = y + max(28, int(height * (0.12 if compact else 0.095)))
        view.add_text_item(
            f"#{order_id}  {order['customer_name']}",
            x + pad_x,
            title_y,
            title_size,
            color="#6f1d1b",
            layer=layer + 10,
            bold=True,
            width=width - pad_x * 2,
            align_center=compact,
            data=data,
        )
        if not compact:
            view.add_text_item(
                f"剩余 {remaining:.0f}s",
                x + pad_x,
                title_y + int(title_size * 1.1),
                max(28, int(title_size * 0.72)),
                color="#7f1d1d",
                layer=layer + 10,
                bold=True,
                width=width - pad_x * 2,
                align_center=True,
                data=data,
            )

        source_lines = lines if lines is not None else self.service.build_order_lines(order_id)
        display_lines = source_lines[:max_lines]
        if len(source_lines) > len(display_lines):
            display_lines = [*display_lines[:-1], "..."]

        line_gap = max(body_size + 8, int(height * (0.075 if compact else 0.044)))
        start_y = y + max(86, int(height * (0.31 if compact else 0.215)))
        for index, text in enumerate(display_lines):
            is_section = text.endswith(":")
            text_x = x + pad_x + (0 if compact or is_section else int(width * 0.035))
            view.add_text_item(
                text,
                text_x,
                start_y + index * line_gap,
                body_size if not is_section else max(body_size, int(body_size * 1.08)),
                color="#7f1d1d" if is_section else "#1f2933",
                layer=layer + 10,
                bold=is_section,
                width=width - pad_x * 2 - (text_x - x - pad_x),
                align_center=False,
                data=data,
            )


    def _render_counter_ticket_paper(
        self,
        view: GameSceneView,
        x: int,
        y: int,
        width: int,
        height: int,
        layer: int,
        mode: str,
        data: str,
    ) -> None:
        """绘制小票纸张底图、阴影、图钉和分隔线。"""
        compact = mode == "hanging"
        radius = max(28, int(width * (0.055 if compact else 0.035)))
        shadow_offset = max(10, int(width * 0.025))
        view.add_rounded_rect_item(
            x + shadow_offset,
            y + shadow_offset + (8 if compact else 18),
            width,
            height,
            radius=radius,
            fill="#52000000",
            outline="transparent",
            layer=layer - 2,
            data=data,
        )
        view.add_rounded_rect_item(
            x,
            y,
            width,
            height,
            radius=radius,
            fill="#FFFDF5E8",
            outline="#F2D8B779",
            layer=layer,
            data=data,
            outline_width=max(3, int(width * 0.007)),
        )

        header_h = max(58, int(height * (0.19 if compact else 0.145)))
        view.add_rounded_rect_item(
            x + int(width * 0.035),
            y + int(height * 0.035),
            width - int(width * 0.07),
            header_h,
            radius=max(20, int(header_h * 0.34)),
            fill="#F6E7C8",
            outline="#E7C98E",
            layer=layer + 1,
            data=data,
            outline_width=max(2, int(width * 0.004)),
        )

        pin_r = max(9, int(width * (0.025 if compact else 0.012)))
        for pin_x in (x + int(width * 0.14), x + width - int(width * 0.14)):
            view.add_rounded_rect_item(
                pin_x - pin_r,
                y + int(height * 0.055),
                pin_r * 2,
                pin_r * 2,
                radius=pin_r,
                fill="#B77A3D",
                outline="#6F3D1D",
                layer=layer + 5,
                data=data,
                outline_width=max(2, pin_r // 5),
            )

        rule_y = y + int(height * (0.26 if compact else 0.205))
        rule_h = max(4, int(height * 0.004))
        dash_w = max(18, int(width * 0.032))
        gap = max(12, int(width * 0.018))
        line_x = x + int(width * 0.09)
        line_end = x + width - int(width * 0.09)
        while line_x < line_end:
            view.add_rect_item(
                line_x,
                rule_y,
                min(dash_w, line_end - line_x),
                rule_h,
                fill="#B9864A",
                outline="transparent",
                layer=layer + 2,
                data=data,
            )
            line_x += dash_w + gap

        if compact:
            return

        margin = int(width * 0.055)
        for row in range(5):
            yy = y + int(height * 0.31) + row * int(height * 0.105)
            view.add_rect_item(
                x + margin,
                yy,
                width - margin * 2,
                max(2, int(height * 0.0025)),
                fill="#22B9864A",
                outline="transparent",
                layer=layer + 1,
                data=data,
            )


    def _render_counter_cash_events(self, view: GameSceneView) -> None:
        """绘制短暂漂浮的收款/退款提示，由 `GameService` 维护 TTL。"""
        for index, event in enumerate(self.service.get_cash_events()[:4]):
            amount = float(event.get("amount", 0.0))
            ttl = float(event.get("ttl", 0.0))
            alpha = max(0.2, min(1.0, ttl / 3.2))
            color = "#166534" if amount >= 0 else "#9a3412"
            text = str(event.get("text", ""))
            item = view.add_text_item(
                text,
                440,
                3530 - index * 150 - int((1.0 - alpha) * 130),
                74,
                color=color,
                layer=210,
                bold=True,
                width=1300,
                align_center=True,
            )
            item.setOpacity(alpha)


    def _counter_completed_orders(self) -> list[dict[str, Any]]:
        """返回已完成点餐、正在等待出餐的活跃订单。"""
        active = self.service.get_active_orders()
        return [
            order
            for order in active
            if int(order["order_id"]) in self._counter_completed_order_ids
        ]
