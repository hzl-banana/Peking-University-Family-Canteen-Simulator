"""业务服务层出口。

UI 层主要通过 `GameService` 完成购买、订单、出餐和日结等操作。
"""

from pku_simulator.services.game_service import GameService

__all__ = ["GameService"]
