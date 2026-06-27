"""游戏业务服务。

这是 Qt UI 和核心数据之间的主接口：商店购买、库存消耗、订单生成、出餐匹配、
日结和设备维修都集中在这里。页面/覆盖层尽量只调用公开方法，不直接改
`GameState` 的内部结构。
"""

from __future__ import annotations

from collections import Counter
import random
from typing import Any

from pku_simulator.core.catalog import CATALOG
from pku_simulator.core.inventory import InventoryManager
from pku_simulator.core.models import GameState
from pku_simulator.core.save_repo import save_state


CUSTOMER_NAMES = ["顾客A", "顾客B", "顾客C", "顾客D", "顾客E"]

# 订单生成、后台控件和商店覆盖层共用的食材 key 组。
GRIDDLE_ORDER_KEYS = [
    "gluten",
    "corn",
    "potato_slice",
    "chicken",
    "pork_belly",
    "bacon",
    "greens",
    "cabbage",
    "tofu",
    "fish_ball",
    "fish_tofu",
    "bean_curd_sheet",
]

CHEUNG_FUN_OPTIONAL_KEYS = ["egg", "shrimp"]

BBQ_SKEWER_KEYS = [
    "raw_lamb_skewer",
    "raw_chicken_wing_skewer",
    "raw_kidney_skewer",
    "raw_pepper_skewer",
    "raw_gluten_skewer",
    "raw_sausage_skewer",
]

GRIDDLE_DUPLICATE_PROBABILITY = 0.18
SERVICE_FIRST_ORDER_SECONDS = 0.0
SERVICE_ORDER_SPAWN_INTERVAL_SECONDS = 30.0
SERVICE_ORDER_SPAWN_END_SECONDS = 150.0
SERVICE_LAST_ORDER_SPAWN_SECONDS = (
    SERVICE_ORDER_SPAWN_END_SECONDS - SERVICE_ORDER_SPAWN_INTERVAL_SECONDS
)
COUNTER_ORDER_LIFETIME_SECONDS = 150.0
COUNTER_SIDE_STATIONS = ["griddle", "cheung_fun", "bbq"]


class GameService:
    """围绕一份 `GameState` 提供业务操作。

    主要调用方：
    - `qt_shop_controller.py`：购买、营业前准备。
    - `qt_pages_workbench.py`：订单计时、日结、出餐仓状态。
    - `qt_counter_controller.py`：点餐台接单/出餐。
    - `qt_workbench_*.py`：工作台完成菜品、标记设备损坏。
    """

    def __init__(self, state: GameState) -> None:
        self.state = state
        self.inventory = InventoryManager(state)

        self._order_id_seq = 1
        self._service_elapsed = 0.0
        self._next_order_spawn_at = SERVICE_FIRST_ORDER_SECONDS
        self._active_orders: list[dict[str, Any]] = []
        self._cash_events: list[dict[str, Any]] = []

    def buy_ingredient(
        self,
        key: str,
        quantity: int = 1,
        price_multiplier: float = 1.0,
    ) -> tuple[bool, str]:
        """商店购买接口；返回 `(是否成功, 给 UI 显示的提示文本)`。"""
        ingredient = CATALOG.get(key)
        if ingredient is None:
            return False, "食材不存在"
        if quantity <= 0:
            return False, "购买数量必须大于 0"

        cost = ingredient.price * max(0.0, price_multiplier) * quantity
        if not self.state.can_spend(cost):
            return False, "余额不足，已达到欠费上限"

        self.state.balance -= cost
        self.inventory.add(key, quantity, self.state.day)
        save_state(self.state)
        return True, f"已购买 {ingredient.name} x{quantity}"

    def get_quantity(self, key: str) -> int:
        """库存查询接口；商店、覆盖层和工作台都会用它更新显示。"""
        return self.inventory.quantity(key)

    def consume_ingredient(self, key: str, quantity: int = 1) -> tuple[bool, str]:
        """工作台取料接口；成功后立即保存。"""
        if quantity <= 0:
            return False, "消耗数量必须大于 0"
        if not self.inventory.consume(key, quantity):
            return False, "库存不足"

        save_state(self.state)
        return True, "已从库存取出食材"

    def mark_station_broken(self, station_key: str, count: int = 1) -> None:
        """工作台损坏登记；次日营业前由 `prepare_for_service_day()` 扣维修费。"""
        if station_key not in self.state.broken_stations:
            self.state.broken_stations[station_key] = 0
        self.state.broken_stations[station_key] += max(0, count)
        save_state(self.state)

    def record_prepared_dish(
        self,
        station: str,
        ingredient_keys: list[str],
        edible: bool,
        cook_seconds: float,
    ) -> None:
        """把某工作台做好的菜写入出餐仓，供点餐台匹配订单。"""
        self.state.prepared_dishes.append(
            {
                "day": self.state.day,
                "station": station,
                "ingredient_keys": list(ingredient_keys),
                "edible": bool(edible),
                "cook_seconds": round(cook_seconds, 2),
            }
        )
        save_state(self.state)

    def prepared_dish_count(self) -> int:
        """返回出餐仓当前菜品数量，给营业区状态栏使用。"""
        return len(self.state.prepared_dishes)

    def tick_counter_orders(self, delta_seconds: float) -> dict[str, list[dict[str, Any]]]:
        """推进点餐台时间轴；返回新增订单和超时赔付事件。"""
        events: dict[str, list[dict[str, Any]]] = {"new_orders": [], "cancelled": []}
        if delta_seconds <= 0:
            return events

        self._service_elapsed += delta_seconds
        self._update_cash_events(delta_seconds)

        while (
            self._service_elapsed <= SERVICE_ORDER_SPAWN_END_SECONDS
            and
            self._next_order_spawn_at <= SERVICE_LAST_ORDER_SPAWN_SECONDS
            and self._service_elapsed >= self._next_order_spawn_at
        ):
            spawn_at = self._next_order_spawn_at
            order = self._create_counter_order(created_at=spawn_at)
            self._active_orders.append(order)
            events["new_orders"].append(self._copy_order(order))
            self._next_order_spawn_at += SERVICE_ORDER_SPAWN_INTERVAL_SECONDS

        remaining_orders: list[dict[str, Any]] = []
        for order in self._active_orders:
            if self._service_elapsed > float(order["deadline_at"]):
                penalty = round(float(order["base_cost"]) * 0.2, 2)
                self.state.balance -= penalty
                self._add_cash_event(-penalty, "订单超时赔付")
                events["cancelled"].append(
                    {
                        "order_id": int(order["order_id"]),
                        "penalty": penalty,
                    }
                )
            else:
                remaining_orders.append(order)

        if len(remaining_orders) != len(self._active_orders):
            self._active_orders = remaining_orders
            save_state(self.state)

        return events

    def get_counter_elapsed_seconds(self) -> float:
        """营业日已过秒数；点餐覆盖层可用它表现时间相关动画。"""
        return self._service_elapsed

    def is_customer_spawn_closed(self) -> bool:
        """是否已停止生成新顾客。"""
        return self._service_elapsed >= SERVICE_ORDER_SPAWN_END_SECONDS

    def should_auto_finish_service_day(self) -> bool:
        """营业是否可自动收餐：不再来客且没有未完成订单。"""
        return self.is_customer_spawn_closed() and not self._active_orders

    def get_active_orders(self) -> list[dict[str, Any]]:
        """返回订单副本给 UI，避免外部直接改内部 `_active_orders`。"""
        return [self._copy_order(order) for order in self._active_orders]

    def get_order_by_id(self, order_id: int) -> dict[str, Any] | None:
        """按订单号取订单副本；点餐台点击清单时使用。"""
        order = self._find_order(order_id)
        if order is None:
            return None
        return self._copy_order(order)

    def pop_next_unannounced_order(self) -> dict[str, Any] | None:
        """取下一张尚未弹出顾客动画的订单，并标记为已通知。"""
        for order in self._active_orders:
            if not bool(order.get("announced", False)):
                order["announced"] = True
                return self._copy_order(order)
        return None

    def get_order_remaining_seconds(self, order_id: int) -> float:
        """返回订单剩余秒数；后台订单列表和覆盖层倒计时共用。"""
        order = self._find_order(order_id)
        if order is None:
            return 0.0
        return max(0.0, float(order["deadline_at"]) - self._service_elapsed)

    def build_order_lines(self, order_id: int) -> list[str]:
        """把订单需求转成人能看的清单文本，供后台表格和点餐覆盖层显示。"""
        order = self._find_order(order_id)
        if order is None:
            return []

        lines: list[str] = ["米饭 1份"]

        griddle_requirements = [
            req
            for req in order["requirements"]
            if req["station"] == "griddle"
        ]
        if griddle_requirements:
            lines.append(f"烤盘 {len(griddle_requirements)}份:")
            for idx, req in enumerate(griddle_requirements, start=1):
                ingredient_keys = list(req["ingredient_keys"])
                if len(griddle_requirements) > 1:
                    lines.append(f"第{idx}锅 · 共 {len(ingredient_keys)}份食材")
                else:
                    lines.append(f"共 {len(ingredient_keys)}份食材")

                for key, quantity in self._count_ingredient_keys(ingredient_keys):
                    suffix = "（重复）" if quantity > 1 else ""
                    lines.append(f"{CATALOG[key].name} {quantity}份{suffix}")

        cheung_fun_requirements = [
            req
            for req in order["requirements"]
            if req["station"] == "cheung_fun"
        ]
        if cheung_fun_requirements:
            req = cheung_fun_requirements[0]
            lines.append("肠粉 1份:")
            for key in req["ingredient_keys"]:
                lines.append(f"{CATALOG[key].name} 1份")

        bbq_requirements = [
            req
            for req in order["requirements"]
            if req["station"] == "bbq"
        ]
        if bbq_requirements:
            lines.append(f"烧烤 {len(bbq_requirements)}串:")
            for req in bbq_requirements:
                skewer_key = req["ingredient_keys"][0]
                tags = [CATALOG[skewer_key].name]
                if "cumin" in req["ingredient_keys"]:
                    tags.append("孜然")
                if "chili" in req["ingredient_keys"]:
                    tags.append("辣椒")
                lines.append(" + ".join(tags))

        return lines

    def preview_order_match(self, order_id: int) -> dict[str, Any]:
        """预检查出餐仓是否能满足订单；`serve_order()` 会复用这个匹配结果。"""
        order = self._find_order(order_id)
        if order is None:
            return {
                "exists": False,
                "can_serve": False,
                "exact_match": False,
                "has_inedible": False,
                "matched_count": 0,
                "required_count": 0,
                "matched_dish_indices": [],
            }

        used_indices: set[int] = set()
        matched_dish_indices: list[int] = []
        exact_match = True
        has_inedible = False
        matched_count = 0

        for req in order["requirements"]:
            req_counts = Counter(req["ingredient_keys"])

            best_idx: int | None = None
            best_score: tuple[int, int, int, int, int] | None = None

            for dish_idx, dish in enumerate(self.state.prepared_dishes):
                if dish_idx in used_indices:
                    continue
                if dish.get("station") != req["station"]:
                    continue

                dish_keys = list(dish.get("ingredient_keys", []))
                dish_counts = Counter(dish_keys)

                overlap = sum(
                    min(req_counts[key], dish_counts.get(key, 0))
                    for key in req_counts
                )
                if overlap <= 0:
                    continue

                missing = sum(
                    max(0, req_counts[key] - dish_counts.get(key, 0))
                    for key in req_counts
                )
                extra = sum(
                    max(0, dish_counts[key] - req_counts.get(key, 0))
                    for key in dish_counts
                )
                exact = 1 if missing == 0 and extra == 0 else 0
                edible = 1 if bool(dish.get("edible", False)) else 0
                score = (-missing, overlap, -extra, exact, edible)

                if best_score is None or score > best_score:
                    best_score = score
                    best_idx = dish_idx

            if best_idx is None:
                exact_match = False
                continue

            used_indices.add(best_idx)
            matched_dish_indices.append(best_idx)

            dish = self.state.prepared_dishes[best_idx]
            dish_counts = Counter(dish.get("ingredient_keys", []))
            missing = sum(
                max(0, req_counts[key] - dish_counts.get(key, 0))
                for key in req_counts
            )
            extra = sum(
                max(0, dish_counts[key] - req_counts.get(key, 0))
                for key in dish_counts
            )

            if missing > 0:
                exact_match = False
            else:
                matched_count += 1

            if extra > 0:
                exact_match = False

            if not bool(dish.get("edible", False)):
                has_inedible = True

        required_count = len(order["requirements"])
        can_serve = matched_count == required_count

        return {
            "exists": True,
            "can_serve": can_serve,
            "exact_match": exact_match,
            "has_inedible": has_inedible,
            "matched_count": matched_count,
            "required_count": required_count,
            "matched_dish_indices": matched_dish_indices,
        }

    def serve_order(self, order_id: int) -> tuple[bool, str, float]:
        """点餐台最终出餐接口；返回 `(是否成功, 提示文本, 实际收入)`。"""
        order = self._find_order(order_id)
        if order is None:
            return False, "订单不存在或已结束", 0.0

        elapsed = self._service_elapsed - float(order["created_at"])
        if elapsed > COUNTER_ORDER_LIFETIME_SECONDS:
            penalty = round(float(order["base_cost"]) * 0.2, 2)
            self.state.balance -= penalty
            self._remove_order(order_id)
            self._add_cash_event(-penalty, "订单超时赔付")
            save_state(self.state)
            return False, "订单已超时，已自动赔付", 0.0

        preview = self.preview_order_match(order_id)
        if not preview["can_serve"]:
            return False, "出餐仓暂时无法满足该订单", 0.0

        base_income = float(order["base_cost"]) * 1.3
        if not preview["exact_match"]:
            base_income *= 0.95

        if preview["has_inedible"]:
            income = 0.0
        else:
            bonus_rate = self._order_bonus_rate(elapsed)
            income = base_income * (1.0 + bonus_rate)

        income = round(max(0.0, income), 2)
        self.state.balance += income

        for dish_idx in sorted(preview["matched_dish_indices"], reverse=True):
            if 0 <= dish_idx < len(self.state.prepared_dishes):
                self.state.prepared_dishes.pop(dish_idx)

        self._remove_order(order_id)
        self._add_cash_event(income, "订单收入")
        save_state(self.state)

        if preview["has_inedible"]:
            return True, "订单已提交，但含不可食用食物，收益为 $ 0.00", income
        if not preview["exact_match"]:
            return True, f"订单已提交，部分不完全匹配，入账 $ {income:.2f}", income
        return True, f"订单已提交，入账 $ {income:.2f}", income

    def get_cash_events(self) -> list[dict[str, Any]]:
        """返回近期收支浮字事件，给点餐台覆盖层渲染。"""
        return [event.copy() for event in self._cash_events]

    def prepare_for_service_day(self) -> tuple[dict[str, int], float]:
        """采购完成后进入营业前调用：清过期、扣维修费、生成第一单。"""
        removed = self.inventory.prune_expired(CATALOG, current_day=self.state.day)

        repaired_slots = sum(self.state.broken_stations.values())
        repair_cost = repaired_slots * 100.0
        if repair_cost > 0:
            self.state.balance -= repair_cost
            for station in list(self.state.broken_stations.keys()):
                self.state.broken_stations[station] = 0

        self._service_elapsed = 0.0
        self._next_order_spawn_at = SERVICE_FIRST_ORDER_SECONDS + SERVICE_ORDER_SPAWN_INTERVAL_SECONDS
        self._active_orders.clear()
        self._cash_events.clear()
        self._active_orders.append(
            self._create_counter_order(created_at=SERVICE_FIRST_ORDER_SECONDS)
        )

        save_state(self.state)
        return removed, repair_cost

    def finish_day(self) -> bool:
        """收餐结算入口；推进天数并返回是否破产。"""
        self.state.prepared_dishes.clear()
        self._service_elapsed = 0.0
        self._next_order_spawn_at = SERVICE_FIRST_ORDER_SECONDS
        self._active_orders.clear()
        self._cash_events.clear()
        self.state.day += 1
        save_state(self.state)
        return self.state.is_game_over()

    def save(self) -> None:
        """给需要显式保存的 UI/工作台模块使用。"""
        save_state(self.state)

    def _copy_order(self, order: dict[str, Any]) -> dict[str, Any]:
        """内部订单转 UI 安全副本；避免 UI 改到服务内部状态。"""
        return {
            "order_id": int(order["order_id"]),
            "customer_name": str(order["customer_name"]),
            "created_at": float(order["created_at"]),
            "deadline_at": float(order["deadline_at"]),
            "base_cost": float(order["base_cost"]),
            "announced": bool(order.get("announced", False)),
            "requirements": [
                {
                    "station": req["station"],
                    "ingredient_keys": list(req["ingredient_keys"]),
                }
                for req in order["requirements"]
            ],
        }

    def _find_order(self, order_id: int) -> dict[str, Any] | None:
        """在内部订单列表中按 id 查找原始订单对象。"""
        for order in self._active_orders:
            if int(order["order_id"]) == order_id:
                return order
        return None

    def _remove_order(self, order_id: int) -> None:
        """出餐或超时后移除订单。"""
        self._active_orders = [
            order for order in self._active_orders if int(order["order_id"]) != order_id
        ]

    def _order_bonus_rate(self, elapsed_seconds: float) -> float:
        """按出餐速度计算奖励比例。"""
        if elapsed_seconds <= 60.0:
            return 0.2

        decay_steps = int((elapsed_seconds - 60.0) // 5.0)
        return max(0.0, 0.2 - decay_steps * 0.05)

    def _add_cash_event(self, amount: float, reason: str) -> None:
        """记录一条临时收支浮字，点餐台覆盖层会消耗这些事件。"""
        rounded = round(amount, 2)
        sign = "+" if rounded >= 0 else "-"
        text = f"{sign} $ {abs(rounded):.2f}"
        self._cash_events.insert(
            0,
            {
                "text": text,
                "amount": rounded,
                "reason": reason,
                "ttl": 3.2,
            },
        )
        self._cash_events = self._cash_events[:6]

    def _update_cash_events(self, delta_seconds: float) -> None:
        """推进收支浮字 TTL，过期后移除。"""
        for event in self._cash_events:
            event["ttl"] = float(event.get("ttl", 0.0)) - delta_seconds
        self._cash_events = [
            event for event in self._cash_events if float(event.get("ttl", 0.0)) > 0.0
        ]

    def _create_counter_order(self, created_at: float | None = None) -> dict[str, Any]:
        """生成一张内部订单 dict；公开给 UI 前要通过 `_copy_order()`。"""
        created_at = self._service_elapsed if created_at is None else float(created_at)
        requirements: list[dict[str, Any]] = [
            {
                "station": "staple",
                "ingredient_keys": ["rice", "water"],
            }
        ]
        base_cost = CATALOG["rice"].price + CATALOG["water"].price

        side_count = random.randint(1, 2)
        side_stations = random.sample(COUNTER_SIDE_STATIONS, k=side_count)
        for side_station in side_stations:
            if side_station == "griddle":
                portions = random.randint(5, 8)
                keys = self._generate_griddle_order_keys(portions)
                requirements.append(
                    {
                        "station": "griddle",
                        "ingredient_keys": keys,
                    }
                )
                for key in keys:
                    base_cost += CATALOG[key].price
            elif side_station == "cheung_fun":
                keys = ["rice_batter"]
                optional_count = random.randint(0, len(CHEUNG_FUN_OPTIONAL_KEYS))
                if optional_count > 0:
                    keys.extend(random.sample(CHEUNG_FUN_OPTIONAL_KEYS, k=optional_count))
                requirements.append(
                    {
                        "station": "cheung_fun",
                        "ingredient_keys": keys,
                    }
                )
                for key in keys:
                    base_cost += CATALOG[key].price
            else:
                skewer_count = random.randint(5, 6)
                for _ in range(skewer_count):
                    skewer_key = random.choice(BBQ_SKEWER_KEYS)
                    ingredient_keys = [skewer_key, "cumin"]
                    if random.random() < 0.45:
                        ingredient_keys.append("chili")

                    requirements.append(
                        {
                            "station": "bbq",
                            "ingredient_keys": ingredient_keys,
                        }
                    )

                    base_cost += CATALOG[skewer_key].price
                    base_cost += CATALOG["cumin"].price
                    if "chili" in ingredient_keys:
                        base_cost += CATALOG["chili"].price

        order = {
            "order_id": self._order_id_seq,
            "customer_name": random.choice(CUSTOMER_NAMES),
            "created_at": created_at,
            "deadline_at": created_at + COUNTER_ORDER_LIFETIME_SECONDS,
            "requirements": requirements,
            "base_cost": round(base_cost, 2),
            "announced": False,
        }
        self._order_id_seq += 1
        return order

    def _generate_griddle_order_keys(self, portions: int) -> list[str]:
        """生成烤盘订单的食材组合，默认尽量不重复，保留少量重复概率。"""
        # Prefer non-repeated ingredient combinations; keep a small chance of duplicates.
        unique_pool = list(GRIDDLE_ORDER_KEYS)
        if portions <= 0:
            return []
        if portions == 1:
            return [random.choice(unique_pool)]

        if random.random() >= GRIDDLE_DUPLICATE_PROBABILITY:
            return random.sample(unique_pool, k=min(portions, len(unique_pool)))

        unique_count = max(3, portions - random.randint(1, min(2, portions - 1)))
        unique_count = min(unique_count, len(unique_pool), portions)
        base_keys = random.sample(unique_pool, k=unique_count)
        keys = list(base_keys)

        while len(keys) < portions:
            keys.append(random.choice(base_keys))

        random.shuffle(keys)
        return keys

    def _count_ingredient_keys(self, ingredient_keys: list[str]) -> list[tuple[str, int]]:
        """把食材 key 列表压缩成 `(key, 数量)`，用于订单清单显示。"""
        counts: dict[str, int] = {}
        for key in ingredient_keys:
            counts[key] = counts.get(key, 0) + 1
        return list(counts.items())
