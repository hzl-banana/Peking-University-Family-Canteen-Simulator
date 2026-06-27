"""页面类统一出口。

旧代码可以继续从 `pku_simulator.qt_pages` 导入页面/后台控件；真实实现已经拆
到 `qt_pages_flow.py`、`qt_pages_workbench.py` 和 `qt_workbench_tabs.py`。
"""

from __future__ import annotations

from pku_simulator.qt_pages_flow import GameOverPage, ShopPage, StartPage
from pku_simulator.qt_pages_workbench import WorkbenchPage
from pku_simulator.qt_workbench_tabs import (
    BbqTab,
    CheungFunTab,
    CounterTab,
    GriddleTab,
    StapleTab,
)

__all__ = [
    "StartPage",
    "ShopPage",
    "WorkbenchPage",
    "GriddleTab",
    "CheungFunTab",
    "StapleTab",
    "BbqTab",
    "CounterTab",
    "GameOverPage",
]
