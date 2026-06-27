"""开始页、商店页和全局音乐面板的 overlay 绘制。

这些方法不处理业务本身，只把按钮/滑块/商品卡绘制到 `GameSceneView`。
交互入口通过图元 `data` 字段暴露给 `qt_click_router.py`：
例如 `buy:{item}:{qty}`、`shop_finish`、`music_settings:*`、`dock:{scene}`。
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


class StartShopOverlayMixin:
    """渲染开始页、采购商店、工作台 dock 和音乐设置浮层。"""

    def _render_music_settings_overlay(self, view: GameSceneView) -> None:
        """绘制右上角音乐按钮；展开后绘制音量滑块、加减按钮和关闭按钮。"""
        button_data = "music_settings:toggle"
        visible = view.visible_scene_rect()
        gear_x, gear_y, gear_w, gear_h, gear_layer = (
            view.store.asset_geometry(MUSIC_GEAR_ASSET_NAME)
        )
        view.add_asset_item(
            MUSIC_GEAR_ASSET_NAME,
            int(visible.x() + gear_x),
            int(visible.y() + gear_y),
            gear_w,
            gear_h,
            layer=gear_layer,
            data=button_data,
        )

        if not self._music_settings_visible:
            return

        panel_data = "music_settings:panel"
        panel_w = 3340
        panel_h = 1640
        panel_x = int(visible.x() + (visible.width() - panel_w) / 2)
        panel_y = int(visible.y() + (visible.height() - panel_h) / 2)
        volume_percent = int(round(self._music_volume * 100))

        view.add_rect_item(
            int(visible.x()),
            int(visible.y()),
            int(visible.width()),
            int(visible.height()),
            fill="#22000000",
            layer=1170,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            panel_x + 42,
            panel_y + 54,
            panel_w,
            panel_h,
            radius=170,
            fill="#55000000",
            layer=1220,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            radius=170,
            fill="#EAF8FBFF",
            outline="#F8FFFFFF",
            layer=1230,
            data=panel_data,
            outline_width=8,
        )
        view.add_rounded_rect_item(
            panel_x + 90,
            panel_y + 76,
            panel_w - 180,
            150,
            radius=75,
            fill="#88FFFFFF",
            outline="#33FFFFFF",
            layer=1231,
            data=panel_data,
        )
        view.add_text_item(
            "背景音乐",
            panel_x + 220,
            panel_y + 300,
            132,
            color="#0f172a",
            layer=1240,
            bold=True,
            width=panel_w - 440,
            align_center=True,
            data=panel_data,
        )
        view.add_text_item(
            self._music_panel_subtitle(),
            panel_x + 220,
            panel_y + 500,
            70,
            color="#475569",
            layer=1240,
            width=panel_w - 440,
            align_center=True,
            data=panel_data,
        )

        slider_x = panel_x + 760
        slider_y = panel_y + 810
        slider_w = 1820
        slider_h = 96
        filled_w = max(slider_h, int(round(slider_w * self._music_volume)))
        knob_size = 190
        knob_x = slider_x + int(round(slider_w * self._music_volume)) - knob_size // 2
        knob_y = slider_y - 48

        view.add_rounded_rect_item(
            slider_x,
            slider_y,
            slider_w,
            slider_h,
            radius=48,
            fill="#D8FFFFFF",
            outline="#99FFFFFF",
            layer=1240,
            data=panel_data,
            outline_width=6,
        )
        view.add_rounded_rect_item(
            slider_x,
            slider_y,
            filled_w,
            slider_h,
            radius=48,
            fill="#C8B91C1C",
            outline="transparent",
            layer=1241,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            knob_x + 16,
            knob_y + 22,
            knob_size,
            knob_size,
            radius=95,
            fill="#44000000",
            layer=1245,
            data=panel_data,
        )
        view.add_rounded_rect_item(
            knob_x,
            knob_y,
            knob_size,
            knob_size,
            radius=95,
            fill="#F8FFFFFF",
            outline="#FFFFFFFF",
            layer=1246,
            data=panel_data,
            outline_width=6,
        )
        view.add_rect_item(
            slider_x,
            slider_y - 96,
            slider_w,
            slider_h + 192,
            fill="#01FFFFFF",
            outline="#01FFFFFF",
            layer=1255,
            data="music_volume_slider",
        )

        for x, text, data in [
            (panel_x + 420, "−", "music_volume_delta:-0.05"),
            (panel_x + panel_w - 680, "+", "music_volume_delta:0.05"),
        ]:
            view.add_rounded_rect_item(
                x,
                slider_y - 72,
                260,
                240,
                radius=100,
                fill="#DFFFFFFF",
                outline="#F8FFFFFF",
                layer=1250,
                data=data,
                outline_width=5,
            )
            view.add_text_item(
                text,
                x,
                slider_y - 54,
                132,
                color="#7f1d1d",
                layer=1260,
                bold=True,
                width=260,
                align_center=True,
                data=data,
            )

        view.add_text_item(
            f"{volume_percent}%",
            panel_x,
            panel_y + 1040,
            86,
            color="#0f172a",
            layer=1260,
            bold=True,
            width=panel_w,
            align_center=True,
            data=panel_data,
        )

        close_data = "music_settings:close"
        close_x = panel_x + panel_w - 390
        close_y = panel_y + 250
        view.add_rounded_rect_item(
            close_x,
            close_y,
            220,
            220,
            radius=90,
            fill="#DFFFFFFF",
            outline="#F8FFFFFF",
            layer=1250,
            data=close_data,
            outline_width=5,
        )
        view.add_text_item(
            "×",
            close_x,
            close_y + 12,
            118,
            color="#7f1d1d",
            layer=1260,
            bold=True,
            width=220,
            align_center=True,
            data=close_data,
        )


    def _music_panel_subtitle(self) -> str:
        """根据当前页面和营业日生成音乐面板副标题。"""
        if self._current_name == "start":
            return "主页 BGM 1 正在循环"
        if self._current_name == "shop":
            return "商店 BGM 2 正在循环"
        if self._current_name == "workbench":
            bgm_no = "3" if self.state.day % 2 else "4"
            return f"第 {self.state.day} 天营业 BGM {bgm_no} 正在循环"
        return "背景音乐"


    def _render_workbench_dock(self, view: GameSceneView, current_scene_key: str) -> None:
        """绘制工作台底部导航 dock，`dock:{scene_key}` 会切换到对应工位。"""
        dock_items = WorkbenchPage.TAB_DOCK_ITEMS
        item_w = 500
        item_h = 430
        gap = 70
        padding_x = 150
        dock_w = len(dock_items) * item_w + (len(dock_items) - 1) * gap + padding_x * 2
        dock_h = 620
        dock_x = int((8640 - dock_w) / 2)
        dock_y = 4870

        view.add_rounded_rect_item(
            dock_x + 30,
            dock_y + 36,
            dock_w,
            dock_h,
            radius=230,
            fill="#55000000",
            layer=940,
        )
        view.add_rounded_rect_item(
            dock_x,
            dock_y,
            dock_w,
            dock_h,
            radius=230,
            fill="#B6F8FBFF",
            outline="#CCFFFFFF",
            layer=950,
            outline_width=6,
        )
        view.add_rounded_rect_item(
            dock_x + 70,
            dock_y + 56,
            dock_w - 140,
            120,
            radius=60,
            fill="#66FFFFFF",
            outline="#33FFFFFF",
            layer=951,
        )

        for index, (scene_key, icon_text, label) in enumerate(dock_items):
            active = scene_key == current_scene_key
            item_x = dock_x + padding_x + index * (item_w + gap)
            item_y = dock_y + 88
            data = f"dock:{scene_key}"

            if active:
                view.add_rounded_rect_item(
                    item_x - 28,
                    item_y - 28,
                    item_w + 56,
                    item_h + 70,
                    radius=120,
                    fill="#E8FFFFFF",
                    outline="#FFFFFFFF",
                    layer=960,
                    data=data,
                    outline_width=5,
                )
                icon_fill = "#DCB91C1C"
                icon_outline = "#FFFFE4E6"
                label_color = "#7f1d1d"
                icon_color = "#ffffff"
            else:
                view.add_rounded_rect_item(
                    item_x,
                    item_y,
                    item_w,
                    item_h,
                    radius=110,
                    fill="#A0FFFFFF",
                    outline="#88FFFFFF",
                    layer=960,
                    data=data,
                    outline_width=4,
                )
                icon_fill = "#B6FFFFFF"
                icon_outline = "#CCFFFFFF"
                label_color = "#0f172a"
                icon_color = "#7f1d1d"

            icon_size = 210 if active else 190
            icon_x = int(item_x + (item_w - icon_size) / 2)
            icon_y = item_y + (38 if active else 50)
            view.add_rounded_rect_item(
                icon_x,
                icon_y,
                icon_size,
                icon_size,
                radius=70,
                fill=icon_fill,
                outline=icon_outline,
                layer=970,
                data=data,
                outline_width=5,
            )
            view.add_text_item(
                icon_text,
                icon_x,
                icon_y + 24,
                104,
                color=icon_color,
                layer=980,
                bold=True,
                width=icon_size,
                align_center=True,
                data=data,
            )
            view.add_text_item(
                label,
                item_x,
                item_y + 282,
                58,
                color=label_color,
                layer=980,
                bold=active,
                width=item_w,
                align_center=True,
                data=data,
            )


    def _render_start_overlay(self, view: GameSceneView) -> None:
        """绘制开始页看板和“开始营业”按钮。"""
        button_data = "开局按钮.jpg"
        balance_value = self._format_start_money(self.state.balance)

        view.add_rect_item(0, 0, 8640, 5592, fill="#3D000000", layer=80)
        view.add_rect_item(0, 3300, 8640, 2292, fill="#55000000", layer=81)

        panel_x = 560
        panel_y = 620
        panel_w = 3500
        panel_h = 3660
        view.add_rect_item(panel_x + 42, panel_y + 48, panel_w, panel_h, fill="#071820", layer=95)
        view.add_rect_item(panel_x, panel_y, panel_w, panel_h, fill="#102b31", outline="#eab35d", layer=100, outline_width=7)
        view.add_rect_item(panel_x + 72, panel_y + 72, panel_w - 144, 20, fill="#eab35d", layer=120)

        view.add_text_item(
            "北大家园食堂模拟器",
            panel_x + 180,
            panel_y + 300,
            210,
            color="#fff7ed",
            layer=130,
            bold=True,
            width=panel_w - 360,
        )
        view.add_text_item(
            "从燕园地标旁开火，把家园食堂经营起来。",
            panel_x + 190,
            panel_y + 670,
            88,
            color="#f8dca7",
            layer=130,
            width=panel_w - 380,
        )

        stats_y = panel_y + 990
        stat_w = 900
        stat_gap = 95
        stat_items = [
            ("营业日", f"第 {self.state.day} 天"),
            ("账户余额", balance_value),
            ("出餐仓", f"{self.service.prepared_dish_count()} 份"),
        ]
        for index, (label, value) in enumerate(stat_items):
            x = panel_x + 190 + index * (stat_w + stat_gap)
            view.add_rect_item(x, stats_y, stat_w, 460, fill="#183f45", outline="#3f6f68", layer=125, outline_width=4)
            view.add_text_item(label, x + 64, stats_y + 58, 64, color="#a7f3d0", layer=135, bold=True, width=stat_w - 128)
            view.add_text_item(value, x + 64, stats_y + 186, 100, color="#fff7ed", layer=135, bold=True, width=stat_w - 128)

        note_x = panel_x + 190
        note_y = panel_y + 1680
        view.add_rect_item(note_x, note_y, panel_w - 380, 520, fill="#0b1f27", outline="#315a59", layer=125, outline_width=4)
        view.add_text_item(
            "今日看板",
            note_x + 90,
            note_y + 70,
            82,
            color="#fbbf24",
            layer=135,
            bold=True,
            width=panel_w - 560,
        )
        view.add_text_item(
            "采购、备餐、出餐，从家园窗口开始。",
            note_x + 90,
            note_y + 210,
            70,
            color="#d1fae5",
            layer=135,
            width=panel_w - 560,
        )
        view.add_text_item(
            "别让饭点队伍等太久。",
            note_x + 90,
            note_y + 342,
            70,
            color="#fef3c7",
            layer=135,
            width=panel_w - 560,
        )

        btn_x = panel_x + 540
        btn_y = panel_y + 2620
        btn_w = 2420
        btn_h = 520
        view.add_rect_item(btn_x + 34, btn_y + 34, btn_w, btn_h, fill="#08151a", layer=135, data=button_data)
        view.add_rect_item(btn_x, btn_y, btn_w, btn_h, fill="#b91c1c", outline="#fed7aa", layer=145, data=button_data, outline_width=8)
        view.add_rect_item(btn_x + 56, btn_y + 46, btn_w - 112, 76, fill="#ef4444", layer=150, data=button_data)
        view.add_text_item(
            "开始营业",
            btn_x,
            btn_y + 96,
            160,
            color="#ffffff",
            layer=160,
            bold=True,
            width=btn_w,
            align_center=True,
            data=button_data,
        )
        view.add_text_item(
            "进入采购",
            btn_x,
            btn_y + 306,
            78,
            color="#fee2e2",
            layer=160,
            width=btn_w,
            align_center=True,
            data=button_data,
        )


    def _format_start_money(self, amount: float) -> str:
        """开始页金额展示专用格式，避免超大余额挤出面板。"""
        sign = "-" if amount < 0 else ""
        value = abs(amount)
        if value >= 1000000000000:
            return f"{sign}${value / 1000000000000:.2f}万亿"
        if value >= 100000000:
            return f"{sign}${value / 100000000:.2f}亿"
        if value >= 10000:
            return f"{sign}${value / 10000:.2f}万"
        return f"{sign}${value:.2f}"


    def _render_shop_overlay(self, view: GameSceneView) -> None:
        """绘制采购商店：背景、余额栏、商品卡和结束采购按钮。"""
        visible = view.visible_scene_rect()
        visible_x = int(visible.x())
        visible_y = int(visible.y())
        visible_w = int(visible.width())
        visible_h = int(visible.height())

        view.add_asset_item(
            SHOP_BACKGROUND_ASSET_NAME,
            visible_x,
            visible_y,
            visible_w,
            visible_h,
            layer=0,
        )
        view.add_rect_item(
            visible_x,
            visible_y,
            visible_w,
            visible_h,
            fill="#48FFF7ED",
            layer=20,
        )
        view.add_rounded_rect_item(
            visible_x + 360,
            visible_y + 170,
            7920,
            520,
            radius=110,
            fill="#F9FFFBF6",
            outline="#E8D6C7B5",
            layer=820,
            outline_width=5,
        )
        view.add_text_item(
            "采购商店",
            visible_x + 620,
            visible_y + 290,
            136,
            color="#7c2d12",
            layer=840,
            bold=True,
        )
        view.add_text_item(
            (
                f"第 {self.state.day} 天    余额: $ {self.state.balance:.2f}    欠费下限: $ {self.state.debt_limit:.2f}"
                + ("    营业中补货价 +20%" if self.shop_price_multiplier() > 1.0 else "")
            ),
            visible_x + 2140,
            visible_y + 286,
            140,
            color="#475569",
            layer=840,
            width=5400,
        )

        for index, item_key in enumerate(SHOP_LIST):
            row = index // SHOP_COLUMNS
            col = index % SHOP_COLUMNS
            card_x = SHOP_START_X + col * (SHOP_CARD_W + SHOP_CARD_GAP_X)
            card_y = SHOP_START_Y + row * (SHOP_CARD_H + SHOP_CARD_GAP_Y)
            self._render_shop_product_card(view, item_key, card_x, card_y)

        rows = (len(SHOP_LIST) + SHOP_COLUMNS - 1) // SHOP_COLUMNS
        finish_y = SHOP_START_Y + rows * (SHOP_CARD_H + SHOP_CARD_GAP_Y) + 70
        finish_data = "shop_finish"
        view.add_rounded_rect_item(
            1180,
            finish_y,
            6280,
            610,
            radius=190,
            fill="#EBD61F1A",
            outline="#FFF8E3A1",
            layer=150,
            data=finish_data,
            outline_width=6,
        )
        view.add_rounded_rect_item(
            1320,
            finish_y + 76,
            6000,
            132,
            radius=66,
            fill="#66FFFFFF",
            outline="#22FFFFFF",
            layer=151,
            data=finish_data,
        )
        view.add_text_item(
            "结束采购",
            1180,
            finish_y + 142,
            146,
            color="#ffffff",
            layer=180,
            width=6280,
            align_center=True,
            bold=True,
            data=finish_data,
        )
        view.add_text_item(
            "返回营业区" if self._shop_opened_from_workbench else "进入营业区",
            1180,
            finish_y + 378,
            74,
            color="#fef3c7",
            layer=180,
            width=6280,
            align_center=True,
            data=finish_data,
        )


    def _render_shop_product_card(
        self,
        view: GameSceneView,
        item_key: str,
        card_x: int,
        card_y: int,
    ) -> None:
        """绘制单个商品卡，按钮 data 为 `buy:{item_key}:{quantity}`。"""
        ingredient = CATALOG[item_key]
        quantity = self.service.get_quantity(item_key)
        unit_price = self.shop_unit_price(item_key)
        badge_text, badge_fill, badge_text_color = SHOP_CATEGORY_BADGES[ingredient.category]
        image_box_x = card_x + 72
        image_box_y = card_y + 88
        image_box_size = 560
        text_x = card_x + 690
        text_w = SHOP_CARD_W - 790
        badge_w = 450
        badge_h = 135
        badge_x = card_x + SHOP_CARD_W - badge_w - 42
        badge_y = card_y + 34
        glass_opacity = view.store.shop_glass_opacity()

        view.add_rounded_rect_item(
            card_x + 18,
            card_y + 28,
            SHOP_CARD_W,
            SHOP_CARD_H,
            radius=92,
            fill=_alpha_color("#000000", glass_opacity * 0.55),
            outline="transparent",
            layer=116,
        )
        view.add_rounded_rect_item(
            card_x,
            card_y,
            SHOP_CARD_W,
            SHOP_CARD_H,
            radius=92,
            fill=_alpha_color("#FFFFFF", glass_opacity),
            outline=_alpha_color("#FFFFFF", min(1.0, glass_opacity + 0.35)),
            layer=120,
            outline_width=4,
        )
        view.add_rounded_rect_item(
            card_x + 18,
            card_y + 18,
            SHOP_CARD_W - 36,
            210,
            radius=76,
            fill=_alpha_color("#FFFFFF", glass_opacity * 0.68),
            outline="transparent",
            layer=121,
        )
        view.add_rounded_rect_item(
            image_box_x - 26,
            image_box_y - 26,
            image_box_size + 52,
            image_box_size + 52,
            radius=58,
            fill=_alpha_color("#FFFFFF", glass_opacity * 0.55),
            outline=_alpha_color("#FFFFFF", glass_opacity * 0.9),
            layer=122,
            outline_width=3,
        )
        view.add_rounded_rect_item(
            badge_x,
            badge_y,
            badge_w,
            badge_h,
            radius=68,
            fill=badge_fill,
            outline="transparent",
            layer=124,
        )
        view.add_text_item(
            badge_text,
            badge_x,
            badge_y + 20,
            70,
            color=badge_text_color,
            layer=180,
            bold=True,
            width=badge_w,
            align_center=True,
        )

        image_asset_name, image_w, image_h, image_offset_x, image_offset_y = self._shop_product_image_geometry(
            view,
            item_key,
            image_box_size,
        )
        if image_asset_name:
            image_center_x = image_box_x + image_box_size / 2
            image_center_y = image_box_y + image_box_size / 2
            view.add_asset_item(
                image_asset_name,
                int(round(image_center_x + image_offset_x - image_w / 2)),
                int(round(image_center_y + image_offset_y - image_h / 2)),
                image_w,
                image_h,
                layer=130,
            )

        view.add_text_item(
            ingredient.name,
            text_x,
            card_y + 96,
            86,
            color="#0f172a",
            layer=180,
            bold=True,
            width=text_w,
        )
        view.add_text_item(
            f"库存 {quantity}",
            text_x,
            card_y + 238,
            62,
            color="#475569",
            layer=180,
            width=text_w,
        )
        view.add_text_item(
            f"$ {unit_price:.2f} / 份" + (" (+20%)" if self.shop_price_multiplier() > 1.0 else ""),
            text_x,
            card_y + 354,
            74,
            color="#7f1d1d",
            layer=180,
            bold=True,
            width=text_w,
        )

        button_y = card_y + 606
        self._render_shop_buy_button(
            view,
            item_key,
            1,
            card_x + 680,
            button_y,
            "购买1个",
        )
        self._render_shop_buy_button(
            view,
            item_key,
            5,
            card_x + 1290,
            button_y,
            "购买5个",
        )


    def _shop_product_image_geometry(
        self,
        view: GameSceneView,
        item_key: str,
        default_size: int,
    ) -> tuple[str | None, int, int, int, int]:
        """优先使用布局编辑器保存的商品图位置，否则回退到默认素材尺寸。"""
        layout_asset_name = SHOP_LAYOUT_ASSET_NAMES_BY_KEY.get(item_key)
        if layout_asset_name and view.store.asset_metadata(layout_asset_name):
            x, y, width, height, _layer = view.store.asset_geometry(layout_asset_name)
            base_x, base_y = self._shop_layout_base_position(item_key)
            return layout_asset_name, width, height, x - base_x, y - base_y

        source_asset_name = SHOP_ASSET_NAMES_BY_KEY.get(item_key)
        if source_asset_name:
            return source_asset_name, default_size, default_size, 0, 0
        return None, default_size, default_size, 0, 0


    def _shop_layout_base_position(self, item_key: str) -> tuple[int, int]:
        """计算商店布局素材的基准格点，用来转换成商品卡内偏移。"""
        try:
            index = SHOP_LIST.index(item_key)
        except ValueError:
            index = 0
        row = index // SHOP_LAYOUT_BASE_COLUMNS
        col = index % SHOP_LAYOUT_BASE_COLUMNS
        return (
            SHOP_LAYOUT_BASE_X + col * SHOP_LAYOUT_BASE_STEP_X,
            SHOP_LAYOUT_BASE_Y + row * SHOP_LAYOUT_BASE_STEP_Y,
        )


    def _render_shop_buy_button(
        self,
        view: GameSceneView,
        item_key: str,
        quantity: int,
        x: int,
        y: int,
        label: str,
    ) -> None:
        """绘制购买按钮；余额不足时不给 data，点击路由会自然忽略。"""
        ingredient = CATALOG[item_key]
        cost = self.shop_unit_price(item_key) * quantity
        enabled = self.state.can_spend(cost)
        data = f"buy:{item_key}:{quantity}" if enabled else None
        fill = "#DDB91C1C" if enabled else "#D8CBD5E1"
        outline = "#FFFEE2E2" if enabled else "#FFE2E8F0"
        text_color = "#ffffff" if enabled else "#64748b"

        view.add_rounded_rect_item(
            x,
            y,
            570,
            172,
            radius=86,
            fill=fill,
            outline=outline,
            layer=160,
            data=data,
            outline_width=4,
        )
        view.add_text_item(
            label,
            x,
            y + 30,
            62,
            color=text_color,
            layer=180,
            bold=True,
            width=570,
            align_center=True,
            data=data,
        )
