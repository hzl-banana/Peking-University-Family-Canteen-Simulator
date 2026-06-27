"""兼容旧入口的 Qt App 包装。

如果旧代码曾经 `from pku_simulator.app import App`，这里仍然把它映射到新的
`QtApp` 实现，避免入口迁移时断掉。
"""

from __future__ import annotations

from pku_simulator.qt_app import QtApp


class App(QtApp):
    """Qt runtime compatibility entry.

    The project has migrated to Qt. Keep `App` as an alias so existing imports
    remain usable.
    """


def main() -> None:
    """从兼容入口启动 Qt 应用。"""
    App().run()


if __name__ == "__main__":
    main()
