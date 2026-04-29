from __future__ import annotations
from pathlib import Path

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal

from codesync.config.config_manager import ConfigManager
from codesync.utils.constants import APP_NAME

_ASSETS_DIR = Path(__file__).parent.parent / "assets"


def _icon(name: str) -> QIcon:
    path = _ASSETS_DIR / name
    if path.exists():
        return QIcon(str(path))
    # Fallback: create a coloured square icon programmatically
    from PyQt6.QtGui import QPixmap, QPainter, QColor
    px = QPixmap(16, 16)
    colors = {"idle.png": "#27ae60", "syncing.png": "#2980b9", "error.png": "#e74c3c"}
    px.fill(QColor(colors.get(name, "#95a5a6")))
    return QIcon(px)


class TrayIcon(QSystemTrayIcon):
    open_requested = pyqtSignal()
    sync_now_requested = pyqtSignal(str)   # profile_id
    quit_requested = pyqtSignal()

    def __init__(self, config_manager: ConfigManager, parent: QObject | None = None):
        super().__init__(parent)
        self._config_manager = config_manager
        self.setIcon(_icon("idle.png"))
        self.setToolTip(APP_NAME)
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        menu = QMenu()

        open_action = QAction("打开 CodeSync", menu)
        open_action.triggered.connect(self.open_requested)
        menu.addAction(open_action)

        menu.addSeparator()

        # Per-profile quick sync actions
        profiles = self._config_manager.settings.profiles
        if profiles:
            sync_menu = menu.addMenu("立即同步")
            for profile in profiles:
                action = QAction(profile.name, sync_menu)
                pid = profile.id
                action.triggered.connect(lambda checked, p=pid: self.sync_now_requested.emit(p))
                sync_menu.addAction(action)
        menu.addSeparator()

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.quit_requested)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def refresh_menu(self) -> None:
        self._build_menu()

    def set_state(self, state: str) -> None:
        icon_map = {"idle": "idle.png", "syncing": "syncing.png", "error": "error.png"}
        self.setIcon(_icon(icon_map.get(state, "idle.png")))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_requested.emit()

    def notify(self, title: str, message: str) -> None:
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
