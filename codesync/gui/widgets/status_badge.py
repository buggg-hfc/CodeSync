from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

_COLORS = {
    "connected": "#27ae60",
    "connecting": "#f39c12",
    "disconnected": "#95a5a6",
    "error": "#e74c3c",
    "syncing": "#2980b9",
}

_LABELS = {
    "connected": "已连接",
    "connecting": "连接中…",
    "disconnected": "未连接",
    "error": "错误",
    "syncing": "同步中…",
}


class StatusBadge(QLabel):
    def __init__(self, state: str = "disconnected", parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(22)
        self.set_state(state)

    def set_state(self, state: str) -> None:
        color = _COLORS.get(state, _COLORS["disconnected"])
        text = _LABELS.get(state, state)
        self.setText(text)
        self.setStyleSheet(
            f"background-color: {color}; color: white; border-radius: 10px;"
            " padding: 2px 10px; font-size: 12px; font-weight: bold;"
        )
