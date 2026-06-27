"""订单临近超时时的顾客催促浮层。

`MainWindow` 定时刷新时调用 `refresh_order_taunt_overlay()`；这里从
`GameService` 读取活跃订单和剩余秒数，选择需要播放的 30s/10s 提醒文案。
"""

from __future__ import annotations

import random
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from pku_simulator.qt_defs import *


class OrderTauntMixin:
    """管理催促 QLabel 的创建、定位、候选订单筛选和淡出动画。"""

    def _setup_order_taunt_overlay(self, parent: QWidget) -> None:
        """在主窗口上创建透明点击穿透的催促标签。"""
        self._order_taunt_label = QLabel(parent)
        self._order_taunt_label.setAlignment(Qt.AlignCenter)
        self._order_taunt_label.setWordWrap(False)
        self._order_taunt_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._order_taunt_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self._order_taunt_label.setStyleSheet(
            "QLabel {"
            "background-color: rgba(255, 0, 0, 46);"
            "border: 3px solid rgba(255, 0, 0, 135);"
            "border-radius: 24px;"
            "color: #ff0000;"
            "font-size: 38px;"
            "font-weight: 900;"
            "padding: 0 32px;"
            "}"
        )
        self._order_taunt_opacity = QGraphicsOpacityEffect(self._order_taunt_label)
        self._order_taunt_opacity.setOpacity(0.0)
        self._order_taunt_label.setGraphicsEffect(self._order_taunt_opacity)
        self._order_taunt_label.hide()
        self._position_order_taunt_overlay()

    def _position_order_taunt_overlay(self, progress: float = 0.0) -> None:
        """根据窗口大小与动画进度重新定位浮层。"""
        if not hasattr(self, "_order_taunt_label"):
            return
        parent = self._order_taunt_label.parentWidget()
        if parent is None:
            return
        label_h = 92
        label_w = min(max(860, int(parent.width() * 0.72)), max(1, parent.width() - 80))
        label_x = max(0, int((parent.width() - label_w) / 2))
        base_y = max(0, int(parent.height() * 0.42) - label_h // 2)
        label_y = max(0, base_y - int(ORDER_TAUNT_RISE_PIXELS * _ease_out_cubic(progress)))
        self._order_taunt_label.setGeometry(label_x, label_y, label_w, label_h)
        self._order_taunt_label.raise_()

    def refresh_order_taunt_overlay(self) -> None:
        """刷新催促状态：优先插播 10 秒警告，否则延续或启动下一条提示。"""
        active_ids = self._prune_order_taunt_state()
        urgent_candidate = self._next_order_taunt_candidate(active_ids)
        if (
            self._order_taunt_active_key is not None
            and urgent_candidate is not None
            and self._order_taunt_active_key[1] != "10s"
            and urgent_candidate[2] == "10s"
        ):
            self._start_order_taunt(*urgent_candidate)
            return

        if self._order_taunt_active_key is not None:
            if self._update_active_order_taunt():
                return
            self._clear_active_order_taunt()

        candidate = self._next_order_taunt_candidate(active_ids)
        if candidate is None:
            self._order_taunt_label.hide()
            return

        self._start_order_taunt(*candidate)

    def _prune_order_taunt_state(self) -> set[int]:
        """清掉已经完成/取消订单的缓存文案和已展示标记。"""
        active_ids = {int(order["order_id"]) for order in self.service.get_active_orders()}
        self._order_taunt_text_by_key = {
            key: text
            for key, text in self._order_taunt_text_by_key.items()
            if key[0] in active_ids
        }
        self._order_taunt_shown_keys = {
            key
            for key in self._order_taunt_shown_keys
            if key[0] in active_ids
        }
        if (
            self._order_taunt_active_key is not None
            and self._order_taunt_active_key[0] not in active_ids
        ):
            self._clear_active_order_taunt()
        return active_ids

    def _next_order_taunt_candidate(
        self,
        active_ids: set[int],
    ) -> tuple[int, str, str] | None:
        """从活跃订单中挑出下一条应该展示的 30s/10s 催促。"""
        candidates: list[tuple[int, float, int, str, str]] = []
        for order in self.service.get_active_orders():
            order_id = int(order["order_id"])
            if order_id not in active_ids:
                continue
            remaining = self.service.get_order_remaining_seconds(order_id)
            if remaining <= 0.0 or remaining > ORDER_TAUNT_30_SECOND_THRESHOLD:
                continue
            stage = (
                "10s"
                if remaining <= ORDER_TAUNT_10_SECOND_THRESHOLD
                else "30s"
            )
            key = (order_id, stage)
            if key in self._order_taunt_shown_keys:
                continue
            stage_priority = 0 if stage == "10s" else 1
            candidates.append(
                (stage_priority, remaining, order_id, str(order["customer_name"]), stage)
            )

        if not candidates:
            return None

        _stage_priority, _remaining, order_id, customer_name, stage = min(candidates)
        return order_id, customer_name, stage

    def _start_order_taunt(self, order_id: int, customer_name: str, stage: str) -> None:
        """启动一条催促动画，并把该订单阶段标记为已经展示。"""
        key = (order_id, stage)
        self._order_taunt_shown_keys.add(key)
        self._order_taunt_active_key = key
        self._order_taunt_active_text = (
            f"{customer_name}：{self._order_taunt_line(order_id, stage)}"
        )
        self._order_taunt_started_at = time.monotonic()
        self._order_taunt_label.setText(self._order_taunt_active_text)
        self._order_taunt_opacity.setOpacity(1.0)
        self._position_order_taunt_overlay(0.0)
        self._order_taunt_label.show()

    def _update_active_order_taunt(self) -> bool:
        """推进当前催促的透明度和上浮位置；返回是否仍在播放。"""
        elapsed = time.monotonic() - self._order_taunt_started_at
        progress = elapsed / ORDER_TAUNT_DISPLAY_SECONDS
        if progress >= 1.0:
            return False

        fade_progress = _clamped_ratio(progress)
        self._order_taunt_opacity.setOpacity(1.0 - fade_progress * fade_progress)
        self._position_order_taunt_overlay(_clamped_ratio(progress))
        self._order_taunt_label.show()
        return True

    def _clear_active_order_taunt(self) -> None:
        """隐藏催促浮层并重置当前播放状态。"""
        self._order_taunt_active_key = None
        self._order_taunt_active_text = ""
        self._order_taunt_started_at = 0.0
        self._order_taunt_opacity.setOpacity(0.0)
        self._order_taunt_label.hide()

    def _order_taunt_line(self, order_id: int, stage: str) -> str:
        """按订单和阶段缓存随机文案，避免同一提醒刷新时反复换词。"""
        key = (order_id, stage)
        cached = self._order_taunt_text_by_key.get(key)
        if cached is not None:
            return cached

        library = (
            ORDER_TAUNT_10_SECOND_LINES
            if stage == "10s"
            else ORDER_TAUNT_30_SECOND_LINES
        )
        line = random.choice(library)
        self._order_taunt_text_by_key[key] = line
        return line
