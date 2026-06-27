"""商店流程控制。

图形商店覆盖层发出 `buy:*` 和 `shop_finish` 点击后，会经
`GraphicalClickRouterMixin` 转到这里。这里再调用 `GameService` 执行购买、
营业前准备和补货返回。
"""

from __future__ import annotations

from pku_simulator.core.catalog import CATALOG
from pku_simulator.qt_defs import SHOP_WORKBENCH_PRICE_MULTIPLIER
from pku_simulator.qt_pages import ShopPage


class ShopControllerMixin:
    """主窗口的商店接口；页面和覆盖层都通过这些方法拿价格/完成采购。"""

    def _setup_shop_state(self) -> None:
        """初始化商店上下文：开局采购和营业中补货使用不同价格倍率。"""
        self._shop_price_multiplier = 1.0
        self._shop_opened_from_workbench = False

    def open_start_shop(self) -> None:
        """从开始页进入采购，使用基础价格。"""
        self._shop_price_multiplier = 1.0
        self._shop_opened_from_workbench = False
        self.change_screen("shop")

    def open_workbench_shop(self) -> None:
        """从营业区进入补货商店，使用营业中加价。"""
        self._shop_price_multiplier = SHOP_WORKBENCH_PRICE_MULTIPLIER
        self._shop_opened_from_workbench = True
        self.change_screen("shop")

    def shop_price_multiplier(self) -> float:
        """给商店页面/覆盖层读取当前价格倍率。"""
        return self._shop_price_multiplier

    def shop_unit_price(self, item_key: str) -> float:
        """按当前价格倍率返回商品单价。"""
        ingredient = CATALOG[item_key]
        return ingredient.price * self._shop_price_multiplier

    def buy_shop_ingredient(self, item_key: str, quantity: int = 1) -> tuple[bool, str]:
        """购买按钮接口；直接转调 `GameService.buy_ingredient()`。"""
        return self.service.buy_ingredient(
            item_key,
            quantity=quantity,
            price_multiplier=self._shop_price_multiplier,
        )

    def finish_shop_purchase(self) -> None:
        """完成采购：补货返回营业区；开局采购则准备当天营业。"""
        page = self._pages.get("shop")
        if self._shop_opened_from_workbench:
            if isinstance(page, ShopPage):
                page._set_message("补货完成，返回营业区", success=True)
            self.change_screen("workbench")
            return

        removed, repair_cost = self.service.prepare_for_service_day()
        if isinstance(page, ShopPage):
            if removed:
                count = sum(removed.values())
                page._set_message(f"已清理过期食材 {count} 份", success=False)
            elif repair_cost > 0:
                page._set_message(f"已扣除设备维修费 $ {repair_cost:.2f}", success=False)
            else:
                page._set_message("采购完成，进入营业区", success=True)

        if self.state.is_game_over():
            self.change_screen("game_over")
        else:
            self.change_screen("workbench")
