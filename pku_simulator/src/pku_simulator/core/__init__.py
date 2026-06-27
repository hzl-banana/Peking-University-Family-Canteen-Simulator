"""纯数据层出口。

这里重新导出食材目录和状态模型，方便其它模块从 `pku_simulator.core` 取核心
类型；本包不依赖 Qt。
"""

from pku_simulator.core.catalog import CATALOG, SHOP_LIST
from pku_simulator.core.models import GameState, IngredientDef

__all__ = ["CATALOG", "SHOP_LIST", "GameState", "IngredientDef"]
