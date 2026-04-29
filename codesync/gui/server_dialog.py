from __future__ import annotations
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox,
    QCheckBox, QVBoxLayout, QFileDialog, QWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor

from codesync.config.models import ServerProfile
from codesync.config.config_manager import ConfigManager


def _req(text: str) -> QLabel:
    """Label with a red asterisk for required fields."""
    lbl = QLabel(f"{text} <span style='color:red'>*</span>")
    lbl.setTextFormat(Qt.TextFormat.RichText)
    return lbl


class _TestThread(QThread):
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


class ServerDialog(QDialog):
    """Dialog for creating or editing a server connection profile."""

    def __init__(self, config_manager: ConfigManager,
                 profile: ServerProfile | None = None, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._profile = profile
        self._editing = profile is not None
        self._test_thread: _TestThread | None = None

        self.setWindowTitle("编辑服务器" if self._editing else "新建服务器")
        self.setMinimumWidth(480)
        self._build_ui()
        if self._editing:
            self._populate()
        else:
            self._auth_changed(0)  # default: show password section (index 0 = 密码)

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("例：开发服务器")
        form.addRow(_req("名称"), self._name_edit)

        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("192.168.1.100 或 example.com")
        form.addRow(_req("主机地址"), self._host_edit)

        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(22)
        form.addRow("端口：", self._port_spin)

        self._user_edit = QLineEdit()
        form.addRow(_req("用户名"), self._user_edit)

        self._auth_combo = QComboBox()
        self._auth_combo.addItems(["密码", "SSH 密钥"])
        self._auth_combo.currentIndexChanged.connect(self._auth_changed)
        form.addRow("认证方式：", self._auth_combo)

        # ── Password section ───────────────────────────────────────────────
        self._pw_section = QWidget()
        pw_form = QFormLayout(self._pw_section)
        pw_form.setContentsMargins(0, 0, 0, 0)
        self._pw_edit = QLineEdit()
        self._pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw_edit.setPlaceholderText("SSH 登录密码")
        pw_form.addRow("密码：", self._pw_edit)
        form.addRow(self._pw_section)

        # ── Key section ────────────────────────────────────────────────────
        self._key_section = QWidget()
        key_form = QFormLayout(self._key_section)
        key_form.setContentsMargins(0, 0, 0, 0)

        key_row = QWidget()
        kl = QHBoxLayout(key_row)
        kl.setContentsMargins(0, 0, 0, 0)
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText(str(Path.home() / ".ssh" / "id_ed25519"))
        kl.addWidget(self._key_edit)
        browse_btn = QPushButton("浏览…")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_key)
        kl.addWidget(browse_btn)
        key_form.addRow("私钥文件：", key_row)

        self._passphrase_edit = QLineEdit()
        self._passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._passphrase_edit.setPlaceholderText("（如有密钥密码请填写）")
        key_form.addRow("密钥密码：", self._passphrase_edit)
        form.addRow(self._key_section)

        # ── Keepalive ──────────────────────────────────────────────────────
        keepalive_row = QWidget()
        kl2 = QHBoxLayout(keepalive_row)
        kl2.setContentsMargins(0, 0, 0, 0)
        self._keepalive_check = QCheckBox("启用保持活跃消息")
        self._keepalive_check.setChecked(True)
        self._keepalive_check.toggled.connect(self._keepalive_toggled)
        kl2.addWidget(self._keepalive_check)
        self._keepalive_spin = QSpinBox()
        self._keepalive_spin.setRange(10, 3600)
        self._keepalive_spin.setValue(60)
        self._keepalive_spin.setSuffix(" 秒")
        kl2.addWidget(self._keepalive_spin)
        kl2.addStretch()
        form.addRow("Keepalive：", keepalive_row)

        root.addLayout(form)

        # ── Test connection ────────────────────────────────────────────────
        test_row = QHBoxLayout()
        self._test_btn = QPushButton("测试连接")
        self._test_btn.setFixedWidth(100)
        self._test_btn.clicked.connect(self._test_connection)
        test_row.addWidget(self._test_btn)
        self._conn_status = QLabel("")
        self._conn_status.setFixedHeight(24)
        test_row.addWidget(self._conn_status, stretch=1)
        root.addLayout(test_row)

        # ── Buttons ────────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确认")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ── Slots ──────────────────────────────────────────────────────────────

    def _auth_changed(self, index: int) -> None:
        is_pw = index == 0
        self._pw_section.setVisible(is_pw)
        self._key_section.setVisible(not is_pw)

    def _keepalive_toggled(self, checked: bool) -> None:
        self._keepalive_spin.setEnabled(checked)

    def _browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择私钥文件", str(Path.home() / ".ssh")
        )
        if path:
            self._key_edit.setText(path)

    def _test_connection(self) -> None:
        profile = self._build_profile()
        if not profile:
            return
        password = self._pw_edit.text() if self._auth_combo.currentIndex() == 0 else ""
        passphrase = self._passphrase_edit.text()
        self._test_btn.setEnabled(False)
        self._set_conn_status("testing", "测试中…")
        self._test_thread = _TestThread(profile, password, passphrase)
        self._test_thread.result.connect(self._on_test_result)
        self._test_thread.start()

    def _on_test_result(self, ok: bool, msg: str) -> None:
        self._test_btn.setEnabled(True)
        if ok:
            self._set_conn_status("ok", "✓ 连接成功")
        else:
            self._set_conn_status("error", f"✗ 连接失败：{msg}")

    def _set_conn_status(self, state: str, text: str) -> None:
        colors = {"ok": "#27ae60", "error": "#e74c3c", "testing": "#f39c12"}
        color = colors.get(state, "#555")
        self._conn_status.setText(text)
        self._conn_status.setStyleSheet(f"color: {color}; font-size: 12px;")

    # ── Build / accept / populate ──────────────────────────────────────────

    def _build_profile(self) -> ServerProfile | None:
        name = self._name_edit.text().strip()
        host = self._host_edit.text().strip()
        user = self._user_edit.text().strip()
        errors = []
        if not name:
            errors.append("名称")
        if not host:
            errors.append("主机地址")
        if not user:
            errors.append("用户名")
        if errors:
            for field_name, edit in [("名称", self._name_edit),
                                      ("主机地址", self._host_edit),
                                      ("用户名", self._user_edit)]:
                if field_name in errors:
                    edit.setStyleSheet("border: 1px solid red;")
                else:
                    edit.setStyleSheet("")
            self._set_conn_status("error", f"请填写必填项：{'、'.join(errors)}")
            return None
        for edit in (self._name_edit, self._host_edit, self._user_edit):
            edit.setStyleSheet("")

        auth = "password" if self._auth_combo.currentIndex() == 0 else "key"
        keepalive = self._keepalive_spin.value() if self._keepalive_check.isChecked() else 0
        return ServerProfile(
            id=self._profile.id if self._profile else "",
            name=name,
            hostname=host,
            port=self._port_spin.value(),
            username=user,
            auth_type=auth,
            key_path=self._key_edit.text().strip(),
            keepalive_interval=keepalive,
            enabled=self._profile.enabled if self._profile else True,
        )

    def _accept(self) -> None:
        profile = self._build_profile()
        if not profile:
            return

        if profile.auth_type == "password":
            self._config_manager.save_credential(profile.id, "password", self._pw_edit.text())
        else:
            self._config_manager.save_credential(profile.id, "passphrase", self._passphrase_edit.text())

        if self._editing:
            self._config_manager.update_profile(profile)
        else:
            self._config_manager.add_profile(profile)
        self.accept()

    def _populate(self) -> None:
        p = self._profile
        self._name_edit.setText(p.name)
        self._host_edit.setText(p.hostname)
        self._port_spin.setValue(p.port)
        self._user_edit.setText(p.username)
        self._auth_combo.setCurrentIndex(0 if p.auth_type == "password" else 1)
        self._key_edit.setText(p.key_path)
        checked = p.keepalive_interval > 0
        self._keepalive_check.setChecked(checked)
        self._keepalive_spin.setValue(p.keepalive_interval if checked else 60)
        self._keepalive_spin.setEnabled(checked)

        if p.auth_type == "password":
            self._pw_edit.setText(self._config_manager.load_credential(p.id, "password"))
        else:
            self._passphrase_edit.setText(self._config_manager.load_credential(p.id, "passphrase"))
