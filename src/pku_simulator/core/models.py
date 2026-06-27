"""核心数据模型。

这些 dataclass 是存档 JSON 和业务服务之间的共同格式。Qt 层通常不直接改
字段，而是通过 `GameService` 或工作台 mixin 间接更新。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IngredientCategory(str, Enum):
    """食材大类；主要供烤盘计时、商店分类和订单生成判断使用。"""

    VEGETABLE = "vegetable"
    MEAT = "meat"
    STAPLE = "staple"
    SKEWER = "skewer"
    SEASONING = "seasoning"
    OTHER = "other"


@dataclass(frozen=True)
class IngredientDef:
    """食材目录项；`catalog.CATALOG` 中每个 key 都对应一个定义。"""

    key: str
    name: str
    price: float
    category: IngredientCategory
    max_age_days: int = 999


@dataclass
class InventoryBatch:
    """同一种食材的一批采购记录，用 purchase_day 支持先进先出和过期清理。"""

    quantity: int
    purchase_day: int

    def to_dict(self) -> dict[str, int]:
        return {
            "quantity": self.quantity,
            "purchase_day": self.purchase_day,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InventoryBatch":
        return cls(
            quantity=int(data.get("quantity", 0)),
            purchase_day=int(data.get("purchase_day", 1)),
        )


@dataclass
class GameState:
    """可序列化的整局游戏状态。

    `save_repo` 负责读写它，`GameService` 负责对它做业务修改，Qt 页面只读
    展示或通过服务层触发修改。
    """

    day: int = 1
    balance: float = 1000.0
    debt_limit: float = -100.0
    game_over_debt: float = -200.0
    inventory: dict[str, list[InventoryBatch]] = field(default_factory=dict)
    prepared_dishes: list[dict[str, Any]] = field(default_factory=list)
    broken_stations: dict[str, int] = field(
        default_factory=lambda: {
            "griddle": 0,
            "cheung_fun": 0,
            "rice_cooker": 0,
        }
    )

    def is_game_over(self) -> bool:
        """余额低于破产线时由页面导航切到失败页。"""
        return self.balance <= self.game_over_debt

    def can_spend(self, amount: float) -> bool:
        """商店购买前调用，确保不会超过允许欠费上限。"""
        return (self.balance - amount) >= self.debt_limit

    def to_dict(self) -> dict[str, Any]:
        """写入 `save/game_state.json` 前转换成 JSON 友好的 dict。"""
        return {
            "day": self.day,
            "balance": round(self.balance, 2),
            "debt_limit": self.debt_limit,
            "game_over_debt": self.game_over_debt,
            "inventory": {
                key: [batch.to_dict() for batch in batches]
                for key, batches in self.inventory.items()
            },
            "prepared_dishes": list(self.prepared_dishes),
            "broken_stations": dict(self.broken_stations),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameState":
        """从存档恢复；对缺失/脏字段做保守兜底。"""
        inventory_data = data.get("inventory", {})
        inventory: dict[str, list[InventoryBatch]] = {}
        for key, batch_list in inventory_data.items():
            inventory[key] = [InventoryBatch.from_dict(batch) for batch in batch_list]

        broken_stations = data.get("broken_stations", {})
        if not isinstance(broken_stations, dict):
            broken_stations = {}

        prepared_dishes = data.get("prepared_dishes", [])
        if not isinstance(prepared_dishes, list):
            prepared_dishes = []
        safe_dishes = [item for item in prepared_dishes if isinstance(item, dict)]

        return cls(
            day=int(data.get("day", 1)),
            balance=float(data.get("balance", 1000.0)),
            debt_limit=float(data.get("debt_limit", -100.0)),
            game_over_debt=float(data.get("game_over_debt", -200.0)),
            inventory=inventory,
            prepared_dishes=safe_dishes,
            broken_stations={
                "griddle": int(broken_stations.get("griddle", 0)),
                "cheung_fun": int(broken_stations.get("cheung_fun", 0)),
                "rice_cooker": int(broken_stations.get("rice_cooker", 0)),
            },
        )
