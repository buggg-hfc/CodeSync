from __future__ import annotations
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QVBoxLayout, QFileDialog, QMessageBox, QTabWidget, QWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from codesync.config.models import ServerProfile, SyncConfig
from codesync.config.config_manager import ConfigManager
from codesync.gui.widgets.path_picker import PathPickerWidget
from codesync.gui.widgets.exclusion_editor import ExclusionEditorWidget
from codesync.utils.constants import DEFAULT_EXCLUSION_PATTERNS, DEFAULT_SYNC_INTERVAL


class _TestConnectionThread(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, profile: ServerProfile, password: str, passphrase: str):
        super().__init__()
        self._profile = profile
        self._password = password
        self._passphrase = passphrase

    def run(self) -> None:
        from codesync.core.ssh_client import SSHClient
        ok, msg = SSHClient.test_connection(self._profile, self._password, self._passphrase)
        self.result.emit(ok, msg)


class ProfileDialog(QDialog):
    """Dialog for creating or editing a server profile and its sync config."""

    def __init__(self, config_manager: ConfigManager, profile: ServerProfile | None = None, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._profile = profile
        self._test_thread: _TestConnectionThread | None = None
        self._editing = profile is not None

        self.setWindowTitle("编辑配置" if self._editing else "新建配置")
        self.setMinimumWidth(500)
        self._build_ui()
        if self._editing:
            self._populate()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._build_connection_tab(), "连接")
        tabs.addTab(self._build_sync_tab(), "同步")
        root.addWidget(tabs)

        # Test connection button
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        root.addWidget(test_btn)
        self._test_btn = test_btn

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_connection_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("例：开发服务器")
        form.addRow("名称：", self._name_edit)

        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("192.168.1.100 或 example.com")
        form.addRow("主机地址：", self._host_edit)

        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(22)
        form.addRow("端口：", self._port_spin)

        self._user_edit = QLineEdit()
        form.addRow("用户名：", self._user_edit)

        self._auth_combo = QComboBox()
        self._auth_combo.addItems(["SSH 密钥", "密码"])
        self._auth_combo.currentIndexChanged.connect(self._auth_changed)
        form.addRow("认证方式：", self._auth_combo)

        # Key path row
        self._key_row_widget = QWidget()
        key_layout = QHBoxLayout(self._key_row_widget)
        key_layout.setContentsMargins(0, 0, 0, 0)
        self._key_edit = QLineEdit()
        default_key = str(Path.home() / ".ssh" / "id_ed25519")
        self._key_edit.setPlaceholderText(default_key)
        key_layout.addWidget(self._key_edit)
        key_browse = QPushButton("浏览…")
        key_browse.setFixedWidth(70)
        key_browse.clicked.connect(self._browse_key)
        key_layout.addWidget(key_browse)
        form.addRow("私钥文件：", self._key_row_widget)

        self._passphrase_edit = QLineEdit()
        self._passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._passphrase_edit.setPlaceholderText("（如有）")
        form.addRow("密钥密码：", self._passphrase_edit)

        # Password row
        self._pw_row_widget = QWidget()
        pw_layout = QHBoxLayout(self._pw_row_widget)
        pw_layout.setContentsMargins(0, 0, 0, 0)
        self._pw_edit = QLineEdit()
        self._pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        pw_layout.addWidget(self._pw_edit)
        form.addRow("SSH 密码：", self._pw_row_widget)

        self._pw_row_widget.setVisible(False)
        return w

    def _build_sync_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._local_path = PathPickerWidget()
        form.addRow("本地目录：", self._local_path)

        self._remote_path_edit = QLineEdit()
        self._remote_path_edit.setPlaceholderText("/home/user/project")
        form.addRow("远程目录：", self._remote_path_edit)

        self._sync_mode_combo = QComboBox()
        self._sync_mode_combo.addItems(["服务器 → 本地", "双向同步"])
        form.addRow("同步方向：", self._sync_mode_combo)

        self._trigger_combo = QComboBox()
        self._trigger_combo.addItems(["手动", "定时", "本地监控"])
        self._trigger_combo.currentIndexChanged.connect(self._trigger_changed)
        form.addRow("触发方式：", self._trigger_combo)

        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(10, 86400)
        self._interval_spin.setValue(DEFAULT_SYNC_INTERVAL)
        self._interval_spin.setSuffix(" 秒")
        form.addRow("同步间隔：", self._interval_spin)

        self._crlf_check = QCheckBox("下载后转换换行符为 CRLF（Windows 风格）")
        form.addRow("", self._crlf_check)

        layout.addLayout(form)

        self._excl_editor = ExclusionEditorWidget()
        self._excl_editor.set_patterns(DEFAULT_EXCLUSION_PATTERNS)
        layout.addWidget(self._excl_editor)

        self._trigger_changed(0)
        return w

    # ── Slots ──────────────────────────────────────────────────────────────

    def _auth_changed(self, index: int) -> None:
        is_key = index == 0
        self._key_row_widget.setVisible(is_key)
        self._passphrase_edit.parentWidget().findChild(QLabel)
        self._pw_row_widget.setVisible(not is_key)

    def _trigger_changed(self, index: int) -> None:
        self._interval_spin.setEnabled(index == 1)  # 1 = 定时

    def _browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择私钥文件", str(Path.home() / ".ssh"))
        if path:
            self._key_edit.setText(path)

    def _test_connection(self) -> None:
        profile = self._build_profile()
        if not profile:
            return
        password = self._pw_edit.text() if self._auth_combo.currentIndex() == 1 else ""
        passphrase = self._passphrase_edit.text()
        self._test_btn.setEnabled(False)
        self._test_btn.setText("测试中…")
        self._test_thread = _TestConnectionThread(profile, password, passphrase)
        self._test_thread.result.connect(self._on_test_result)
        self._test_thread.start()

    def _on_test_result(self, ok: bool, msg: str) -> None:
        self._test_btn.setEnabled(True)
        self._test_btn.setText("测试连接")
        if ok:
            QMessageBox.information(self, "连接成功", msg)
        else:
            QMessageBox.warning(self, "连接失败", msg)

    # ── Accept / populate ──────────────────────────────────────────────────

    def _build_profile(self) -> ServerProfile | None:
        name = self._name_edit.text().strip()
        host = self._host_edit.text().strip()
        user = self._user_edit.text().strip()
        if not name or not host or not user:
            QMessageBox.warning(self, "输入不完整", "请填写名称、主机地址和用户名。")
            return None
        auth = "key" if self._auth_combo.currentIndex() == 0 else "password"
        profile_id = self._profile.id if self._profile else ""
        return ServerProfile(
            id=profile_id,
            name=name,
            hostname=host,
            port=self._port_spin.value(),
            username=user,
            auth_type=auth,
            key_path=self._key_edit.text().strip(),
        )

    def _accept(self) -> None:
        profile = self._build_profile()
        if not profile:
            return

        sync_modes = ["server_to_local", "bidirectional"]
        triggers = ["manual", "interval", "watch"]
        sync_config = SyncConfig(
            profile_id=profile.id,
            local_path=self._local_path.path(),
            remote_path=self._remote_path_edit.text().strip(),
            sync_mode=sync_modes[self._sync_mode_combo.currentIndex()],
            trigger=triggers[self._trigger_combo.currentIndex()],
            interval_seconds=self._interval_spin.value(),
            exclusion_patterns=self._excl_editor.patterns(),
            line_ending="crlf" if self._crlf_check.isChecked() else "keep",
        )

        # Save credentials
        if profile.auth_type == "password":
            self._config_manager.save_credential(profile.id, "password", self._pw_edit.text())
        else:
            self._config_manager.save_credential(profile.id, "passphrase", self._passphrase_edit.text())

        if self._editing:
            self._config_manager.update_profile(profile)
        else:
            self._config_manager.add_profile(profile)
        self._config_manager.save_sync_config(sync_config)

        self.accept()

    def _populate(self) -> None:
        p = self._profile
        self._name_edit.setText(p.name)
        self._host_edit.setText(p.hostname)
        self._port_spin.setValue(p.port)
        self._user_edit.setText(p.username)
        self._auth_combo.setCurrentIndex(0 if p.auth_type == "key" else 1)
        self._key_edit.setText(p.key_path)

        cfg = self._config_manager.get_sync_config(p.id)
        if cfg:
            self._local_path.set_path(cfg.local_path)
            self._remote_path_edit.setText(cfg.remote_path)
            sync_modes = ["server_to_local", "bidirectional"]
            if cfg.sync_mode in sync_modes:
                self._sync_mode_combo.setCurrentIndex(sync_modes.index(cfg.sync_mode))
            triggers = ["manual", "interval", "watch"]
            if cfg.trigger in triggers:
                self._trigger_combo.setCurrentIndex(triggers.index(cfg.trigger))
            self._interval_spin.setValue(cfg.interval_seconds)
            self._excl_editor.set_patterns(cfg.exclusion_patterns)
            self._crlf_check.setChecked(cfg.line_ending == "crlf")

        # Load saved credentials
        if p.auth_type == "password":
            pw = self._config_manager.load_credential(p.id, "password")
            self._pw_edit.setText(pw)
        else:
            pp = self._config_manager.load_credential(p.id, "passphrase")
            self._passphrase_edit.setText(pp)
