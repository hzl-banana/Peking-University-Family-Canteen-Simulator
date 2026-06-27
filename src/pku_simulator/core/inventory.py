"""库存批次管理。

`GameService` 持有一个 `InventoryManager`，Qt 层不要直接改库存 dict；通过
这里可以统一处理先进先出消耗和过期清理。
"""

from pku_simulator.core.models import GameState, IngredientDef, InventoryBatch


class InventoryManager:
    """库存操作接口；入参都是食材 key，状态写回 `GameState.inventory`。"""

    def __init__(self, state: GameState) -> None:
        self.state = state

    def quantity(self, key: str) -> int:
        """返回某个食材当前所有批次的总数量。"""
        batches = self.state.inventory.get(key, [])
        return sum(batch.quantity for batch in batches)

    def add(self, key: str, quantity: int, purchase_day: int) -> None:
        """商店购买入口；同一天购买会合并到同一个批次。"""
        if quantity <= 0:
            return

        batches = self.state.inventory.setdefault(key, [])
        for batch in batches:
            if batch.purchase_day == purchase_day:
                batch.quantity += quantity
                return

        batches.append(InventoryBatch(quantity=quantity, purchase_day=purchase_day))

    def consume(self, key: str, quantity: int) -> bool:
        """工作台取料入口；成功返回 True，并从最早批次开始扣。"""
        if quantity <= 0:
            return True
        if self.quantity(key) < quantity:
            return False

        batches = self.state.inventory.get(key, [])
        # Consume oldest batches first so expiration is naturally handled.
        batches.sort(key=lambda item: item.purchase_day)
        remain = quantity

        for batch in batches:
            if remain <= 0:
                break
            take = min(batch.quantity, remain)
            batch.quantity -= take
            remain -= take

        self.state.inventory[key] = [batch for batch in batches if batch.quantity > 0]
        if not self.state.inventory[key]:
            del self.state.inventory[key]
        return True

    def prune_expired(self, catalog: dict[str, IngredientDef], current_day: int) -> dict[str, int]:
        """每天营业前清理过期批次，返回被清掉的 key -> 数量。"""
        removed: dict[str, int] = {}

        for key in list(self.state.inventory.keys()):
            definition = catalog.get(key)
            max_age_days = definition.max_age_days if definition else 999

            keep_batches: list[InventoryBatch] = []
            removed_count = 0

            for batch in self.state.inventory[key]:
                age_days = current_day - batch.purchase_day
                if age_days <= max_age_days:
                    keep_batches.append(batch)
                else:
                    removed_count += batch.quantity

            if removed_count > 0:
                removed[key] = removed_count

            if keep_batches:
                self.state.inventory[key] = keep_batches
            else:
                del self.state.inventory[key]

        return removed
