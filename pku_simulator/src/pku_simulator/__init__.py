"""PKU Simulator 核心包。

依赖方向约定为 `core -> services -> Qt UI`：数据层不依赖 Qt，业务层只操作
`GameState`，Qt 层通过服务/控制器调用业务接口。
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
