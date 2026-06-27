"""顶部余额浮层。

主窗口继承此 mixin 后，在营业区和营业中补货商店顶部显示余额，不参与场景
坐标系统，因此跟随窗口大小单独定位。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget


class BalanceNotchMixin:
    """余额浮层接口；依赖主窗口的 `state`、`_current_name` 和商店上下文。"""

    def _setup_balance_notch_overlay(self, parent: QWidget) -> None:
        """创建黑色余额标签，父级是主窗口中央容器。"""
        self._balance_notch_label = QLabel(parent)
        self._balance_notch_label.setAlignment(Qt.AlignCenter)
        self._balance_notch_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._balance_notch_label.setStyleSheet(
            "QLabel {"
            "background-color: #050505;"
            "border: 1px solid rgba(255, 255, 255, 65);"
            "border-bottom-left-radius: 18px;"
            "border-bottom-right-radius: 18px;"
            "color: #ffffff;"
            "font-size: 17px;"
            "font-weight: 800;"
            "letter-spacing: 0px;"
            "padding: 0 26px;"
            "}"
        )
        self._refresh_balance_notch()
        self._position_balance_notch_overlay()
        self._balance_notch_label.raise_()

    def _position_balance_notch_overlay(self) -> None:
        """窗口尺寸变化时重新居中定位。"""
        if not hasattr(self, "_balance_notch_label"):
            return
        parent = self._balance_notch_label.parentWidget()
        if parent is None:
            return
        notch_w = min(max(320, int(parent.width() * 0.26)), 460)
        notch_h = 38
        notch_x = max(0, int((parent.width() - notch_w) / 2))
        self._balance_notch_label.setGeometry(notch_x, 0, notch_w, notch_h)
        self._balance_notch_label.raise_()

    def _refresh_balance_notch(self) -> None:
        """刷新余额文本和可见性。"""
        if not hasattr(self, "_balance_notch_label"):
            return
        visible = self._balance_notch_should_show()
        self._balance_notch_label.setText(f"余额：$ {self.state.balance:.2f}")
        self._balance_notch_label.setVisible(visible)
        if visible:
            self._balance_notch_label.raise_()

    def _balance_notch_should_show(self) -> bool:
        """只在营业区和营业中补货商店显示。"""
        current_name = getattr(self, "_current_name", "")
        if current_name == "workbench":
            return True
        return current_name == "shop" and self._shop_opened_from_workbench
