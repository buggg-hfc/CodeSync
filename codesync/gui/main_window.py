from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QTabWidget, QMessageBox, QSplitter,
    QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QCloseEvent

from codesync.config.config_manager import ConfigManager
from codesync.config.models import ServerProfile
from codesync.gui.sync_tab import SyncTab
from codesync.gui.log_tab import LogTab
from codesync.gui.settings_tab import SettingsTab
from codesync.gui.profile_dialog import ProfileDialog
from codesync.utils.constants import APP_NAME, APP_VERSION
from codesync import core


class MainWindow(QMainWindow):
    closed = pyqtSignal()

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self._config_manager = config_manager
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(QSize(800, 560))
        self._build_ui()
        self._refresh_profile_list()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # Left panel — profile list
        left = QWidget()
        left.setFixedWidth(200)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)

        left_layout.addWidget(QLabel("服务器配置"))

        self._profile_list = QListWidget()
        self._profile_list.currentRowChanged.connect(self._on_profile_selected)
        left_layout.addWidget(self._profile_list)

        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("＋ 新建")
        self._add_btn.clicked.connect(self._add_profile)
        btn_row.addWidget(self._add_btn)

        self._edit_btn = QPushButton("编辑")
        self._edit_btn.setEnabled(False)
        self._edit_btn.clicked.connect(self._edit_profile)
        btn_row.addWidget(self._edit_btn)

        self._del_btn = QPushButton("删除")
        self._del_btn.setEnabled(False)
        self._del_btn.clicked.connect(self._delete_profile)
        btn_row.addWidget(self._del_btn)

        left_layout.addLayout(btn_row)
        splitter.addWidget(left)

        # Right panel — tabs
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)

        self._tabs = QTabWidget()
        self._sync_tab = SyncTab(self._config_manager)
        self._log_tab = LogTab()
        self._settings_tab = SettingsTab(self._config_manager)

        self._tabs.addTab(self._sync_tab, "同步")
        self._tabs.addTab(self._log_tab, "日志")
        self._tabs.addTab(self._settings_tab, "设置")
        right_layout.addWidget(self._tabs)
        splitter.addWidget(right)
        splitter.setSizes([200, 600])

    # ── Profile list management ────────────────────────────────────────────

    def _refresh_profile_list(self) -> None:
        self._profile_list.clear()
        for p in self._config_manager.settings.profiles:
            item = QListWidgetItem(p.name)
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self._profile_list.addItem(item)

    def _on_profile_selected(self, row: int) -> None:
        has_selection = row >= 0
        self._edit_btn.setEnabled(has_selection)
        self._del_btn.setEnabled(has_selection)
        if has_selection:
            profile_id = self._profile_list.item(row).data(Qt.ItemDataRole.UserRole)
            profile = self._config_manager.get_profile(profile_id)
            self._sync_tab.set_profile(profile)
        else:
            self._sync_tab.set_profile(None)

    def _add_profile(self) -> None:
        dlg = ProfileDialog(self._config_manager, parent=self)
        if dlg.exec():
            self._refresh_profile_list()
            # Select the newly added profile (last item)
            self._profile_list.setCurrentRow(self._profile_list.count() - 1)

    def _edit_profile(self) -> None:
        row = self._profile_list.currentRow()
        if row < 0:
            return
        profile_id = self._profile_list.item(row).data(Qt.ItemDataRole.UserRole)
        profile = self._config_manager.get_profile(profile_id)
        if profile:
            dlg = ProfileDialog(self._config_manager, profile=profile, parent=self)
            if dlg.exec():
                self._refresh_profile_list()
                self._profile_list.setCurrentRow(row)

    def _delete_profile(self) -> None:
        row = self._profile_list.currentRow()
        if row < 0:
            return
        profile_id = self._profile_list.item(row).data(Qt.ItemDataRole.UserRole)
        profile = self._config_manager.get_profile(profile_id)
        if not profile:
            return
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除配置"{profile.name}"吗？此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._config_manager.delete_profile(profile_id)
            self._refresh_profile_list()

    # ── Window close ──────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        # Minimise to tray instead of closing if tray is available
        self.hide()
        event.ignore()

    def quit(self) -> None:
        """Actually quit the application (called from tray menu)."""
        self.closed.emit()
