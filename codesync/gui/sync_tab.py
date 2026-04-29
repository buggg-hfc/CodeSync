from __future__ import annotations
import time
from datetime import datetime

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
        self._last_sync_time: float | None = None
        self._build_ui()

        # Countdown timer for next scheduled sync
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._update_countdown)

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Status group
        status_group = QGroupBox("连接状态")
        sg_layout = QHBoxLayout(status_group)
        self._badge = StatusBadge("disconnected")
        sg_layout.addWidget(self._badge)
        sg_layout.addStretch()
        self._profile_label = QLabel("未选择配置")
        self._profile_label.setStyleSheet("font-weight: bold;")
        sg_layout.addWidget(self._profile_label)
        layout.addWidget(status_group)

        # Sync controls group
        ctrl_group = QGroupBox("同步控制")
        ctrl_layout = QVBoxLayout(ctrl_group)

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
        ctrl_layout.addLayout(btn_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%v / %m 文件")
        ctrl_layout.addWidget(self._progress_bar)

        self._current_file_label = QLabel("")
        self._current_file_label.setStyleSheet("color: #555; font-size: 11px;")
        self._current_file_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        ctrl_layout.addWidget(self._current_file_label)

        layout.addWidget(ctrl_group)

        # Info group
        info_group = QGroupBox("同步信息")
        info_layout = QVBoxLayout(info_group)
        self._last_sync_label = QLabel("上次同步：—")
        self._next_sync_label = QLabel("下次同步：—")
        self._summary_label = QLabel("")
        self._summary_label.setWordWrap(True)
        info_layout.addWidget(self._last_sync_label)
        info_layout.addWidget(self._next_sync_label)
        info_layout.addWidget(self._summary_label)
        layout.addWidget(info_group)

    # ── Public interface ───────────────────────────────────────────────────

    def set_profile(self, profile: ServerProfile | None) -> None:
        self._profile = profile
        self._config = self._config_manager.get_sync_config(profile.id) if profile else None
        self._profile_label.setText(profile.name if profile else "未选择配置")
        self._badge.set_state("disconnected")
        self._sync_btn.setEnabled(profile is not None)
        self._summary_label.setText("")
        self._current_file_label.setText("")
        self._progress_bar.setValue(0)

    # ── Sync control ───────────────────────────────────────────────────────

    def _start_sync(self) -> None:
        if not self._profile or not self._config:
            return
        if self._worker and self._worker.isRunning():
            return

        self._badge.set_state("syncing")
        self._sync_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._progress_bar.setValue(0)
        self._progress_bar.setRange(0, 0)  # indeterminate until total known
        self._current_file_label.setText("连接中…")
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
        self._current_file_label.setText(filename)

    def _on_finished(self, summary: SyncSummary) -> None:
        self._badge.set_state("connected")
        self._sync_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._current_file_label.setText("")
        self._last_sync_time = summary.timestamp
        ts = datetime.fromtimestamp(summary.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        self._last_sync_label.setText(f"上次同步：{ts}")
        err_text = f"，{len(summary.errors)} 个错误" if summary.errors else ""
        conflict_text = f"，{summary.conflicts} 个冲突" if summary.conflicts else ""
        self._summary_label.setText(
            f"同步完成：{summary.files_synced} 个文件已同步，"
            f"{summary.files_deleted} 个已删除{err_text}{conflict_text}，"
            f"耗时 {summary.duration_seconds:.1f}s"
        )

    def _on_error(self, msg: str) -> None:
        self._badge.set_state("error")
        self._sync_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._current_file_label.setText("")
        self._summary_label.setText(f"错误：{msg}")

    def _update_countdown(self) -> None:
        if not self._config or self._config.trigger != "interval":
            self._next_sync_label.setText("下次同步：—")
            return
        # placeholder — actual next-fire time would come from the scheduler
        self._next_sync_label.setText("自动同步已启用")
