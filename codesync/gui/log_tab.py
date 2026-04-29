from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QGuiApplication

from codesync.utils.logger import get_ring_handler, set_qt_bridge


class _LogBridge(QObject):
    """Qt object that lives on the main thread and receives log lines from any thread."""
    new_log_line = pyqtSignal(str)


class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._setup_bridge()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(2000)
        self._log_view.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 12px;"
        )
        layout.addWidget(self._log_view)

        btn_row = QHBoxLayout()
        clear_btn = QPushButton("清除日志")
        clear_btn.clicked.connect(self._log_view.clear)
        copy_btn = QPushButton("复制到剪贴板")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_row.addStretch()
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(copy_btn)
        layout.addLayout(btn_row)

    def _setup_bridge(self) -> None:
        self._bridge = _LogBridge()
        self._bridge.new_log_line.connect(self._append_line)
        set_qt_bridge(self._bridge)

        # Populate with existing ring buffer content
        for line in get_ring_handler().get_lines():
            self._log_view.appendPlainText(line)

    def _append_line(self, line: str) -> None:
        self._log_view.appendPlainText(line)
        # Auto-scroll to bottom
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _copy_to_clipboard(self) -> None:
        text = self._log_view.toPlainText()
        QGuiApplication.clipboard().setText(text)
