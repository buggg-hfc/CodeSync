from __future__ import annotations
from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QGroupBox, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer

from codesync.config.config_manager import ConfigManager
from codesync.config.models import ServerProfile, SyncConfig
from codesync.core.sync_engine import SyncSummary
from codesync.gui.widgets.status_badge import StatusBadge
from codesync.workers.sync_worker import SyncWorker


class SyncTab(QWidget):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._profile: ServerProfile | None = None
        self._config: SyncConfig | None = None
        self._worker: SyncWorker | None = None
        self._build_ui()

        # Updates "下次同步" every second
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._update_next_sync_label)
        self._countdown_timer.start()

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Status group
        status_group = QGroupBox("当前配置")
        sg = QHBoxLayout(status_group)
        self._badge = StatusBadge("disconnected")
        sg.addWidget(self._badge)
        self._profile_label = QLabel("未选择配置")
        self._profile_label.setStyleSheet("font-weight: bold;")
        sg.addWidget(self._profile_label)
        sg.addStretch()
        self._dir_label = QLabel("")
        self._dir_label.setStyleSheet("color: #555; font-size: 11px;")
        sg.addWidget(self._dir_label)
        layout.addWidget(status_group)

        # Sync controls
        ctrl_group = QGroupBox("同步控制")
        ctrl = QVBoxLayout(ctrl_group)

        btn_row = QHBoxLayout()
        self._sync_btn = QPushButton("立即同步")
        self._sync_btn.setFixedHeight(36)
        self._sync_btn.clicked.connect(self._start_sync)
        self._sync_btn.setEnabled(False)
        btn_row.addWidget(self._sync_btn)

        self._stop_btn = QPushButton("停止")
        self._stop_btn.setFixedHeight(36)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_sync)
        btn_row.addWidget(self._stop_btn)
        ctrl.addLayout(btn_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("就绪")
        ctrl.addWidget(self._progress_bar)

        self._current_file_label = QLabel("")
        self._current_file_label.setStyleSheet("color: #555; font-size: 11px;")
        self._current_file_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        ctrl.addWidget(self._current_file_label)
        layout.addWidget(ctrl_group)

        # Info group
        info_group = QGroupBox("同步信息")
        info = QVBoxLayout(info_group)
        self._last_sync_label = QLabel("上次同步：—")
        self._next_sync_label = QLabel("下次同步：—")
        self._summary_label = QLabel("")
        self._summary_label.setWordWrap(True)
        info.addWidget(self._last_sync_label)
        info.addWidget(self._next_sync_label)
        info.addWidget(self._summary_label)
        layout.addWidget(info_group)

    # ── Public interface ───────────────────────────────────────────────────

    def set_active(self, profile: ServerProfile | None, config: SyncConfig | None) -> None:
        """Called when the user selects a profile/sync-dir in the tree."""
        self._profile = profile
        self._config = config
        if profile:
            self._profile_label.setText(f"{profile.name}  ({profile.hostname})")
        else:
            self._profile_label.setText("未选择配置")
        if config:
            self._dir_label.setText(f"{config.remote_path} → {config.local_path}")
        else:
            self._dir_label.setText("")
        self._badge.set_state("disconnected")
        self._sync_btn.setEnabled(profile is not None and config is not None)
        self._summary_label.setText("")
        self._current_file_label.setText("")
        self._reset_progress()
        self._update_next_sync_label()

    # ── Sync control ───────────────────────────────────────────────────────

    def _start_sync(self) -> None:
        if not self._profile or not self._config:
            return
        if self._worker and self._worker.isRunning():
            return

        self._badge.set_state("syncing")
        self._sync_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._progress_bar.setRange(0, 0)   # indeterminate spinner
        self._progress_bar.setFormat("连接中…")
        self._current_file_label.setText("")
        self._summary_label.setText("")

        self._worker = SyncWorker(self._profile, self._config, self._config_manager)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _stop_sync(self) -> None:
        if self._worker:
            self._worker.request_stop()
        self._stop_btn.setEnabled(False)

    # ── Worker signal handlers ─────────────────────────────────────────────

    def _on_progress(self, done: int, total: int, filename: str) -> None:
        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(done)
            self._progress_bar.setFormat(f"%v / %m 个文件")
        self._current_file_label.setText(filename)

    def _on_finished(self, summary: SyncSummary) -> None:
        self._badge.set_state("connected")
        self._sync_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._current_file_label.setText("")

        ts = datetime.fromtimestamp(summary.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        self._last_sync_label.setText(f"上次同步：{ts}")

        if summary.files_synced == 0 and summary.files_deleted == 0 and not summary.errors:
            self._progress_bar.setRange(0, 1)
            self._progress_bar.setValue(1)
            self._progress_bar.setFormat("已是最新，无需同步")
            self._summary_label.setText(f"无变化，耗时 {summary.duration_seconds:.1f}s")
        else:
            self._progress_bar.setRange(0, 1)
            self._progress_bar.setValue(1)
            self._progress_bar.setFormat("同步完成")
            err_text = f"，{len(summary.errors)} 个错误" if summary.errors else ""
            conflict_text = f"，{summary.conflicts} 个冲突" if summary.conflicts else ""
            self._summary_label.setText(
                f"已同步 {summary.files_synced} 个文件，"
                f"删除 {summary.files_deleted} 个{err_text}{conflict_text}，"
                f"耗时 {summary.duration_seconds:.1f}s"
            )
        self._update_next_sync_label()

    def _on_error(self, msg: str) -> None:
        self._badge.set_state("error")
        self._sync_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._reset_progress("错误")
        self._current_file_label.setText("")
        self._summary_label.setText(f"错误：{msg}")

    # ── Next sync time ─────────────────────────────────────────────────────

    def _update_next_sync_label(self) -> None:
        if not self._config:
            self._next_sync_label.setText("下次同步：—")
            return

        has_auto = any(t.type in ("interval", "daily") for t in self._config.triggers)
        if not has_auto:
            self._next_sync_label.setText("下次同步：手动触发")
            return

        from codesync.core import scheduler as sched
        next_times = sched.get_next_run_times_for_config(self._config.id)
        if next_times:
            earliest = min(next_times)
            local_dt = earliest.astimezone().replace(tzinfo=None)
            self._next_sync_label.setText(
                f"下次同步：{local_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            self._next_sync_label.setText("下次同步：自动同步已启用（待触发）")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _reset_progress(self, label: str = "就绪") -> None:
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat(label)
