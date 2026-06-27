"""命令行/包入口。

`pyproject.toml` 的 `pku-simulator` 命令会调用这里的 `main()`，再进入 Qt
应用封装 `QtApp`。
"""

from pku_simulator.qt_app import QtApp


def main() -> None:
    """启动 Qt 应用主循环。"""
    app = QtApp()
    app.run()


if __name__ == "__main__":
    main()
