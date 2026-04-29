from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QCheckBox, QComboBox, QPushButton,
    QGroupBox, QVBoxLayout, QSpinBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from codesync.config.config_manager import ConfigManager


class SettingsTab(QWidget):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Behaviour group
        behaviour_group = QGroupBox("行为设置")
        form = QFormLayout(behaviour_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._start_min_check = QCheckBox("启动时最小化到托盘")
        form.addRow("", self._start_min_check)

        self._notify_check = QCheckBox("同步完成后显示系统通知")
        form.addRow("", self._notify_check)

        layout.addWidget(behaviour_group)

        # Appearance group
        appearance_group = QGroupBox("外观设置")
        app_form = QFormLayout(appearance_group)
        app_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(8, 24)
        self._font_size_spin.setValue(14)
        self._font_size_spin.setSuffix(" pt")
        app_form.addRow("界面字体大小：", self._font_size_spin)

        layout.addWidget(appearance_group)

        # Logging group
        log_group = QGroupBox("日志设置")
        log_form = QFormLayout(log_group)
        log_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._log_level_combo = QComboBox()
        self._log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_form.addRow("日志级别：", self._log_level_combo)

        layout.addWidget(log_group)

        save_btn = QPushButton("保存设置")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()

    def _load(self) -> None:
        s = self._config_manager.settings
        self._start_min_check.setChecked(s.start_minimized)
        self._notify_check.setChecked(s.show_notifications)
        self._font_size_spin.setValue(s.font_size)
        idx = ["DEBUG", "INFO", "WARNING", "ERROR"].index(s.log_level.upper())
        self._log_level_combo.setCurrentIndex(max(0, idx))

    def _save(self) -> None:
        from PyQt6.QtWidgets import QApplication
        s = self._config_manager.settings
        s.start_minimized = self._start_min_check.isChecked()
        s.show_notifications = self._notify_check.isChecked()
        s.log_level = self._log_level_combo.currentText()
        s.font_size = self._font_size_spin.value()
        self._config_manager.save()

        app = QApplication.instance()
        if app:
            font = app.font()
            font.setPointSize(s.font_size)
            app.setFont(font)
