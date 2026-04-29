from __future__ import annotations
from pathlib import Path, PurePosixPath

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox,
    QCheckBox, QVBoxLayout, QListWidget, QListWidgetItem,
    QGroupBox, QWidget, QTimeEdit,
)
from PyQt6.QtCore import Qt, QTime

from codesync.config.models import SyncConfig, SyncTrigger, ServerProfile
from codesync.config.config_manager import ConfigManager
from codesync.gui.widgets.path_picker import PathPickerWidget
from codesync.gui.widgets.exclusion_editor import ExclusionEditorWidget
from codesync.utils.constants import DEFAULT_EXCLUSION_PATTERNS, DEFAULT_SYNC_INTERVAL


def _req(text: str) -> QLabel:
    lbl = QLabel(f"{text} <span style='color:red'>*</span>")
    lbl.setTextFormat(Qt.TextFormat.RichText)
    return lbl


class SyncDirDialog(QDialog):
    """Dialog for adding or editing a sync directory configuration."""

    def __init__(self, config_manager: ConfigManager, profile: ServerProfile,
                 sync_config: SyncConfig | None = None, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._profile = profile
        self._sync_config = sync_config
        self._editing = sync_config is not None

        self.setWindowTitle("编辑同步目录" if self._editing else "新建同步目录")
        self.setMinimumWidth(540)
        self.setMinimumHeight(520)
        self._build_ui()
        if self._editing:
            self._populate()
        else:
            self._update_local_preview()

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("（留空则使用远程目录名）")
        form.addRow("显示名称：", self._name_edit)

        self._remote_edit = QLineEdit()
        self._remote_edit.setPlaceholderText("/home/user/project")
        self._remote_edit.textChanged.connect(self._update_local_preview)
        form.addRow(_req("远程目录"), self._remote_edit)

        self._local_parent = PathPickerWidget("选择本地父目录…")
        self._local_parent.path_changed.connect(self._update_local_preview)
        form.addRow(_req("本地父目录"), self._local_parent)

        self._local_preview = QLabel("实际同步路径：—")
        self._local_preview.setStyleSheet("color: #555; font-size: 11px;")
        form.addRow("", self._local_preview)

        self._sync_mode_combo = QComboBox()
        self._sync_mode_combo.addItems(["服务器 → 本地（单向）", "双向同步"])
        form.addRow("同步方向：", self._sync_mode_combo)

        self._crlf_check = QCheckBox("下载后转换换行符为 CRLF")
        form.addRow("换行符：", self._crlf_check)

        # Max file size
        size_row = QWidget()
        sl = QHBoxLayout(size_row)
        sl.setContentsMargins(0, 0, 0, 0)
        self._size_check = QCheckBox("跳过大于")
        self._size_check.toggled.connect(lambda c: self._size_spin.setEnabled(c))
        sl.addWidget(self._size_check)
        self._size_spin = QSpinBox()
        self._size_spin.setRange(1, 102400)
        self._size_spin.setValue(500)
        self._size_spin.setSuffix(" MB")
        self._size_spin.setEnabled(False)
        sl.addWidget(self._size_spin)
        sl.addWidget(QLabel("的文件"))
        sl.addStretch()
        form.addRow("大文件过滤：", size_row)

        root.addLayout(form)

        # ── Triggers ───────────────────────────────────────────────────────
        trig_group = QGroupBox("触发方式（可添加多个）")
        tg = QVBoxLayout(trig_group)

        self._trigger_list = QListWidget()
        self._trigger_list.setMaximumHeight(90)
        tg.addWidget(self._trigger_list)

        trig_btn_row = QHBoxLayout()
        add_interval_btn = QPushButton("＋ 间隔触发")
        add_interval_btn.clicked.connect(self._add_interval_trigger)
        add_daily_btn = QPushButton("＋ 每日定时")
        add_daily_btn.clicked.connect(self._add_daily_trigger)
        del_trig_btn = QPushButton("删除选中")
        del_trig_btn.clicked.connect(self._delete_trigger)
        trig_btn_row.addWidget(add_interval_btn)
        trig_btn_row.addWidget(add_daily_btn)
        trig_btn_row.addStretch()
        trig_btn_row.addWidget(del_trig_btn)
        tg.addLayout(trig_btn_row)

        root.addWidget(trig_group)

        # ── Exclusion editor ───────────────────────────────────────────────
        self._excl_editor = ExclusionEditorWidget()
        self._excl_editor.set_patterns(DEFAULT_EXCLUSION_PATTERNS)
        root.addWidget(self._excl_editor)

        # ── Buttons ────────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确认")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ── Trigger management ─────────────────────────────────────────────────

    def _add_interval_trigger(self) -> None:
        dlg = _IntervalDialog(self)
        if dlg.exec():
            t = SyncTrigger(type="interval", interval_seconds=dlg.seconds())
            item = QListWidgetItem(f"间隔 {dlg.seconds()} 秒")
            item.setData(Qt.ItemDataRole.UserRole, t)
            self._trigger_list.addItem(item)

    def _add_daily_trigger(self) -> None:
        dlg = _DailyDialog(self)
        if dlg.exec():
            t = SyncTrigger(type="daily", daily_time=dlg.time_str())
            item = QListWidgetItem(f"每日 {dlg.time_str()}")
            item.setData(Qt.ItemDataRole.UserRole, t)
            self._trigger_list.addItem(item)

    def _delete_trigger(self) -> None:
        row = self._trigger_list.currentRow()
        if row >= 0:
            self._trigger_list.takeItem(row)

    def _triggers(self) -> list[SyncTrigger]:
        result = []
        for i in range(self._trigger_list.count()):
            t = self._trigger_list.item(i).data(Qt.ItemDataRole.UserRole)
            if t:
                result.append(t)
        if not result:
            result = [SyncTrigger(type="manual")]
        return result

    # ── Helpers ────────────────────────────────────────────────────────────

    def _update_local_preview(self) -> None:
        remote = self._remote_edit.text().strip()
        parent = self._local_parent.path()
        if remote and parent:
            remote_name = PurePosixPath(remote).name or PurePosixPath(remote).parts[-1] if PurePosixPath(remote).parts else ""
            if remote_name:
                actual = str(Path(parent) / remote_name)
                self._local_preview.setText(f"实际同步路径：{actual}")
                return
        self._local_preview.setText("实际同步路径：—")

    def _actual_local_path(self) -> str:
        remote = self._remote_edit.text().strip()
        parent = self._local_parent.path()
        if not remote or not parent:
            return ""
        remote_name = PurePosixPath(remote).name
        if not remote_name:
            # remote is like "/" — use last non-empty part
            parts = [p for p in PurePosixPath(remote).parts if p != "/"]
            remote_name = parts[-1] if parts else "sync"
        return str(Path(parent) / remote_name)

    # ── Accept / populate ──────────────────────────────────────────────────

    def _accept(self) -> None:
        remote = self._remote_edit.text().strip()
        parent = self._local_parent.path()
        errors = []
        if not remote:
            errors.append("远程目录")
        if not parent:
            errors.append("本地父目录")
        if errors:
            self._remote_edit.setStyleSheet("" if remote else "border: 1px solid red;")
            return

        actual_local = self._actual_local_path()
        sync_modes = ["server_to_local", "bidirectional"]
        name = self._name_edit.text().strip() or PurePosixPath(remote).name or remote

        config = SyncConfig(
            id=self._sync_config.id if self._sync_config else "",
            profile_id=self._profile.id,
            name=name,
            local_path=actual_local,
            remote_path=remote,
            sync_mode=sync_modes[self._sync_mode_combo.currentIndex()],
            triggers=self._triggers(),
            exclusion_patterns=self._excl_editor.patterns(),
            max_file_size_mb=self._size_spin.value() if self._size_check.isChecked() else 0,
            line_ending="crlf" if self._crlf_check.isChecked() else "keep",
            enabled=self._sync_config.enabled if self._sync_config else True,
        )
        self._config_manager.save_sync_config(config)
        self.accept()

    def _populate(self) -> None:
        c = self._sync_config
        self._name_edit.setText(c.name)
        self._remote_edit.setText(c.remote_path)
        # Infer parent from local_path (reverse of _actual_local_path)
        local = Path(c.local_path)
        self._local_parent.set_path(str(local.parent) if local.parent != local else str(local))
        self._update_local_preview()

        sync_modes = ["server_to_local", "bidirectional"]
        if c.sync_mode in sync_modes:
            self._sync_mode_combo.setCurrentIndex(sync_modes.index(c.sync_mode))
        self._crlf_check.setChecked(c.line_ending == "crlf")
        if c.max_file_size_mb > 0:
            self._size_check.setChecked(True)
            self._size_spin.setValue(c.max_file_size_mb)
            self._size_spin.setEnabled(True)

        self._excl_editor.set_patterns(c.exclusion_patterns)

        self._trigger_list.clear()
        for t in c.triggers:
            if t.type == "interval":
                label = f"间隔 {t.interval_seconds} 秒"
            elif t.type == "daily":
                label = f"每日 {t.daily_time}"
            else:
                label = "手动"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, t)
            self._trigger_list.addItem(item)


# ── Simple sub-dialogs for adding triggers ─────────────────────────────────────

class _IntervalDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("间隔触发")
        layout = QFormLayout(self)
        self._spin = QSpinBox()
        self._spin.setRange(10, 86400)
        self._spin.setValue(DEFAULT_SYNC_INTERVAL)
        self._spin.setSuffix(" 秒")
        layout.addRow("同步间隔：", self._spin)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确认")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def seconds(self) -> int:
        return self._spin.value()


class _DailyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("每日定时触发")
        layout = QFormLayout(self)
        self._time_edit = QTimeEdit(QTime(2, 0))
        self._time_edit.setDisplayFormat("HH:mm")
        layout.addRow("执行时间：", self._time_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("确认")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def time_str(self) -> str:
        return self._time_edit.time().toString("HH:mm")
