from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QTabWidget, QMessageBox, QSplitter, QLabel,
    QTreeWidget, QTreeWidgetItem, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QPoint
from PyQt6.QtGui import QCloseEvent, QColor, QFont

from codesync.config.config_manager import ConfigManager
from codesync.config.models import ServerProfile, SyncConfig
from codesync.gui.sync_tab import SyncTab
from codesync.gui.log_tab import LogTab
from codesync.gui.settings_tab import SettingsTab
from codesync.gui.server_dialog import ServerDialog
from codesync.gui.sync_dir_dialog import SyncDirDialog
from codesync.utils.constants import APP_NAME, APP_VERSION

# Item type stored in UserRole
_ROLE_TYPE = Qt.ItemDataRole.UserRole
_ROLE_ID   = Qt.ItemDataRole.UserRole + 1

_TYPE_PROFILE  = "profile"
_TYPE_SYNCDIR  = "syncdir"

_STATUS_COLORS = {
    "enabled":  "#27ae60",
    "disabled": "#95a5a6",
}

_TREE_STYLESHEET = """
QTreeWidget {
    background: #2b2b2b;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 6px;
    outline: none;
    show-decoration-selected: 0;
}
QTreeWidget::item {
    height: 26px;
    padding-left: 2px;
    border-radius: 4px;
}
QTreeWidget::item:hover {
    background: #3c3c3c;
}
QTreeWidget::item:selected {
    background: #274573;
    color: white;
}
/* 折叠状态：向右箭头 */
QTreeWidget::branch:closed:has-children {
    image: url(codesync/assets/branch-closed.svg);
}
/* 展开状态：向下箭头 */
QTreeWidget::branch:open:has-children {
    image: url(codesync/assets/branch-open.svg);
}
"""

_BTN_PRIMARY = """
QPushButton {
    background: #2a5ca8;
    color: white;
    border-radius: 5px;
    padding: 5px 10px;
    border: none;
    font-size: 12px;
}
QPushButton:hover { background: #0b5ed7; }
QPushButton:disabled { background: #495057; color: #adb5bd; }
"""

_BTN_SECONDARY = """
QPushButton {
    background: #6c757d;
    color: white;
    border-radius: 5px;
    padding: 5px 10px;
    border: none;
    font-size: 12px;
}
QPushButton:hover { background: #5c636a; }
QPushButton:disabled { background: #495057; color: #adb5bd; }
"""


class MainWindow(QMainWindow):
    closed = pyqtSignal()
    config_saved = pyqtSignal(str)  # emits config_id after a sync config is saved/updated

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self._config_manager = config_manager
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(QSize(900, 600))
        self._build_ui()
        self._refresh_tree()

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ── Left: server tree ──────────────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(240)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 6, 0)
        ll.setSpacing(6)

        header_lbl = QLabel("服务器配置")
        header_lbl.setStyleSheet("font-weight: bold; font-size: 13px; padding: 2px 0 4px 2px; color: #e0e0e0;")
        ll.addWidget(header_lbl)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(1)
        self._tree.setExpandsOnDoubleClick(False)
        self._tree.setStyleSheet(_TREE_STYLESHEET)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        self._tree.currentItemChanged.connect(self._on_selection_changed)
        self._tree.setIndentation(16)
        ll.addWidget(self._tree)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._add_server_btn = QPushButton("＋ 服务器")
        self._add_server_btn.setStyleSheet(_BTN_PRIMARY)
        self._add_server_btn.clicked.connect(self._add_server)
        btn_row.addWidget(self._add_server_btn)

        self._add_dir_btn = QPushButton("＋ 目录")
        self._add_dir_btn.setStyleSheet(_BTN_SECONDARY)
        self._add_dir_btn.setEnabled(False)
        self._add_dir_btn.clicked.connect(self._add_sync_dir)
        self._add_dir_btn.setToolTip("先选中一台服务器，再添加同步目录")
        btn_row.addWidget(self._add_dir_btn)
        ll.addLayout(btn_row)
        splitter.addWidget(left)

        # ── Right: tabs ────────────────────────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 0, 0, 0)

        self._tabs = QTabWidget()
        self._sync_tab = SyncTab(self._config_manager)
        self._log_tab = LogTab()
        self._settings_tab = SettingsTab(self._config_manager)
        self._tabs.addTab(self._sync_tab, "同步")
        self._tabs.addTab(self._log_tab, "日志")
        self._tabs.addTab(self._settings_tab, "设置")
        rl.addWidget(self._tabs)
        splitter.addWidget(right)
        splitter.setSizes([240, 660])

    # ── Tree helpers ───────────────────────────────────────────────────────

    def _refresh_tree(self) -> None:
        expanded = set()
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item and item.isExpanded():
                expanded.add(item.data(0, _ROLE_ID))

        self._tree.clear()
        bold_font = QFont()
        bold_font.setBold(True)
        for profile in self._config_manager.settings.profiles:
            p_item = self._make_profile_item(profile, bold_font)
            for cfg in self._config_manager.get_sync_configs_for_profile(profile.id):
                c_item = self._make_syncdir_item(cfg)
                p_item.addChild(c_item)
            self._tree.addTopLevelItem(p_item)
            if profile.id in expanded or not expanded:
                p_item.setExpanded(True)

    def _make_profile_item(self, profile: ServerProfile, bold_font: QFont | None = None) -> QTreeWidgetItem:
        dot = "●" if profile.enabled else "○"
        color = _STATUS_COLORS["enabled"] if profile.enabled else _STATUS_COLORS["disabled"]
        item = QTreeWidgetItem([f"{dot}  {profile.name}"])
        item.setForeground(0, QColor(color))
        if bold_font:
            item.setFont(0, bold_font)
        item.setToolTip(0, f"{profile.hostname}:{profile.port}  ({profile.username})"
                           + ("" if profile.enabled else "  [已禁用]"))
        item.setData(0, _ROLE_TYPE, _TYPE_PROFILE)
        item.setData(0, _ROLE_ID, profile.id)
        return item

    def _make_syncdir_item(self, cfg: SyncConfig) -> QTreeWidgetItem:
        dot = "↔" if cfg.sync_mode == "bidirectional" else "→"
        enabled_dot = "●" if cfg.enabled else "○"
        label = f"{enabled_dot} {dot} {cfg.name or cfg.remote_path}"
        item = QTreeWidgetItem([label])
        color = _STATUS_COLORS["enabled"] if cfg.enabled else _STATUS_COLORS["disabled"]
        item.setForeground(0, QColor(color))
        item.setToolTip(0, f"{cfg.remote_path}  →  {cfg.local_path}")
        item.setData(0, _ROLE_TYPE, _TYPE_SYNCDIR)
        item.setData(0, _ROLE_ID, cfg.id)
        return item

    def _current_profile_id(self) -> str | None:
        item = self._tree.currentItem()
        if not item:
            return None
        if item.data(0, _ROLE_TYPE) == _TYPE_PROFILE:
            return item.data(0, _ROLE_ID)
        parent = item.parent()
        if parent and parent.data(0, _ROLE_TYPE) == _TYPE_PROFILE:
            return parent.data(0, _ROLE_ID)
        return None

    def _current_syncdir_id(self) -> str | None:
        item = self._tree.currentItem()
        if item and item.data(0, _ROLE_TYPE) == _TYPE_SYNCDIR:
            return item.data(0, _ROLE_ID)
        return None

    # ── Selection ──────────────────────────────────────────────────────────

    def _on_selection_changed(self, current, previous) -> None:
        if not current:
            self._add_dir_btn.setEnabled(False)
            self._sync_tab.set_active(None, None)
            return

        item_type = current.data(0, _ROLE_TYPE)
        if item_type == _TYPE_PROFILE:
            profile_id = current.data(0, _ROLE_ID)
            self._add_dir_btn.setEnabled(True)
            cfgs = self._config_manager.get_sync_configs_for_profile(profile_id)
            active_cfg = next((c for c in cfgs if c.enabled), cfgs[0] if cfgs else None)
            profile = self._config_manager.get_profile(profile_id)
            self._sync_tab.set_active(profile, active_cfg)
        elif item_type == _TYPE_SYNCDIR:
            syncdir_id = current.data(0, _ROLE_ID)
            cfg = self._config_manager.get_sync_config(syncdir_id)
            profile_id = cfg.profile_id if cfg else None
            profile = self._config_manager.get_profile(profile_id) if profile_id else None
            self._add_dir_btn.setEnabled(True)
            self._sync_tab.set_active(profile, cfg)

    # ── Double-click to edit ───────────────────────────────────────────────

    def _on_double_click(self, item: QTreeWidgetItem, column: int) -> None:
        if item.data(0, _ROLE_TYPE) == _TYPE_PROFILE:
            self._edit_server(item.data(0, _ROLE_ID))
        elif item.data(0, _ROLE_TYPE) == _TYPE_SYNCDIR:
            self._edit_sync_dir(item.data(0, _ROLE_ID))

    # ── Right-click context menu ───────────────────────────────────────────

    def _on_context_menu(self, pos: QPoint) -> None:
        item = self._tree.itemAt(pos)
        menu = QMenu(self)

        if item is None:
            menu.addAction("＋ 新建服务器", self._add_server)
        elif item.data(0, _ROLE_TYPE) == _TYPE_PROFILE:
            profile_id = item.data(0, _ROLE_ID)
            profile = self._config_manager.get_profile(profile_id)
            menu.addAction("编辑", lambda: self._edit_server(profile_id))
            menu.addAction("＋ 新建同步目录", lambda: self._add_sync_dir_for(profile_id))
            menu.addSeparator()
            if profile and profile.enabled:
                menu.addAction("禁用", lambda: self._toggle_profile_enabled(profile_id, False))
            else:
                menu.addAction("启用", lambda: self._toggle_profile_enabled(profile_id, True))
            menu.addSeparator()
            menu.addAction("删除", lambda: self._delete_server(profile_id))
        elif item.data(0, _ROLE_TYPE) == _TYPE_SYNCDIR:
            syncdir_id = item.data(0, _ROLE_ID)
            cfg = self._config_manager.get_sync_config(syncdir_id)
            menu.addAction("编辑", lambda: self._edit_sync_dir(syncdir_id))
            menu.addSeparator()
            if cfg and cfg.enabled:
                menu.addAction("禁用", lambda: self._toggle_syncdir_enabled(syncdir_id, False))
            else:
                menu.addAction("启用", lambda: self._toggle_syncdir_enabled(syncdir_id, True))
            menu.addSeparator()
            menu.addAction("删除", lambda: self._delete_sync_dir(syncdir_id))

        menu.exec(self._tree.viewport().mapToGlobal(pos))

    # ── Server CRUD ────────────────────────────────────────────────────────

    def _add_server(self) -> None:
        dlg = ServerDialog(self._config_manager, parent=self)
        if dlg.exec():
            self._refresh_tree()

    def _edit_server(self, profile_id: str) -> None:
        profile = self._config_manager.get_profile(profile_id)
        if profile:
            dlg = ServerDialog(self._config_manager, profile=profile, parent=self)
            if dlg.exec():
                self._refresh_tree()

    def _delete_server(self, profile_id: str) -> None:
        profile = self._config_manager.get_profile(profile_id)
        if not profile:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f'确定要删除服务器"{profile.name}"及其所有同步目录吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._config_manager.delete_profile(profile_id)
            self._refresh_tree()

    def _toggle_profile_enabled(self, profile_id: str, enabled: bool) -> None:
        profile = self._config_manager.get_profile(profile_id)
        if not profile:
            return
        profile.enabled = enabled
        self._config_manager.update_profile(profile)
        # Cascade to all sync configs under this profile
        for cfg in self._config_manager.get_sync_configs_for_profile(profile_id):
            cfg.enabled = enabled
            self._config_manager.save_sync_config(cfg)
        self._refresh_tree()

    # ── Sync dir CRUD ──────────────────────────────────────────────────────

    def _add_sync_dir(self) -> None:
        profile_id = self._current_profile_id()
        if profile_id:
            self._add_sync_dir_for(profile_id)

    def _add_sync_dir_for(self, profile_id: str) -> None:
        profile = self._config_manager.get_profile(profile_id)
        if profile:
            dlg = SyncDirDialog(self._config_manager, profile, parent=self)
            if dlg.exec():
                if dlg.saved_config_id:
                    self.config_saved.emit(dlg.saved_config_id)
                self._refresh_tree()

    def _edit_sync_dir(self, syncdir_id: str) -> None:
        cfg = self._config_manager.get_sync_config(syncdir_id)
        if not cfg:
            return
        profile = self._config_manager.get_profile(cfg.profile_id)
        if profile:
            dlg = SyncDirDialog(self._config_manager, profile, sync_config=cfg, parent=self)
            if dlg.exec():
                if dlg.saved_config_id:
                    self.config_saved.emit(dlg.saved_config_id)
                self._refresh_tree()

    def _delete_sync_dir(self, syncdir_id: str) -> None:
        cfg = self._config_manager.get_sync_config(syncdir_id)
        if not cfg:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f'确定要删除同步目录"{cfg.name}"吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._config_manager.delete_sync_config(syncdir_id)
            self._refresh_tree()

    def _toggle_syncdir_enabled(self, syncdir_id: str, enabled: bool) -> None:
        cfg = self._config_manager.get_sync_config(syncdir_id)
        if cfg:
            cfg.enabled = enabled
            self._config_manager.save_sync_config(cfg)
            self._refresh_tree()

    # ── Thread-safe trigger (scheduler/watcher → GUI thread) ───────────────

    @pyqtSlot(str)
    def trigger_sync_for_config(self, config_id: str) -> None:
        cfg = self._config_manager.get_sync_config(config_id)
        if not cfg or not cfg.enabled:
            return
        profile = self._config_manager.get_profile(cfg.profile_id)
        if profile and profile.enabled:
            self._sync_tab.set_active(profile, cfg)
            self._sync_tab._start_sync()

    # ── Window ─────────────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        self.hide()
        event.ignore()

    def quit(self) -> None:
        self.closed.emit()
