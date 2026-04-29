from __future__ import annotations
import sys
import argparse

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QFont

from codesync.utils.constants import APP_NAME
from codesync.utils.logger import setup_logging, logger
from codesync.config.config_manager import ConfigManager
from codesync.config.models import SyncConfig
from codesync.core import scheduler as sched
from codesync.core.file_watcher import FileWatcher


def main() -> None:
    parser = argparse.ArgumentParser(prog="codesync")
    parser.add_argument("--minimized-to-tray", action="store_true")
    args, qt_args = parser.parse_known_args()

    app = QApplication(sys.argv[:1] + qt_args)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    config_manager = ConfigManager()
    settings = config_manager.load()
    setup_logging(settings.log_level)
    logger.info("CodeSync starting up")

    # Apply font size from settings
    font = app.font()
    font.setPointSize(settings.font_size)
    app.setFont(font)

    from codesync.gui.main_window import MainWindow
    from codesync.gui.tray_icon import TrayIcon

    window = MainWindow(config_manager)
    tray = TrayIcon(config_manager)
    tray.setVisible(True)

    tray.open_requested.connect(window.show)
    tray.open_requested.connect(window.raise_)
    tray.quit_requested.connect(_shutdown)
    window.closed.connect(_shutdown)

    def _sync_from_tray(config_id: str) -> None:
        cfg = config_manager.get_sync_config(config_id)
        if cfg and cfg.enabled:
            profile = config_manager.get_profile(cfg.profile_id)
            if profile and profile.enabled:
                window.show()
                window.raise_()
                window._sync_tab.set_active(profile, cfg)
                window._sync_tab._start_sync()

    tray.sync_now_requested.connect(_sync_from_tray)

    file_watcher = FileWatcher()
    _bridges = _start_auto_sync(config_manager, file_watcher, window)

    # Re-register scheduler jobs whenever a sync config is added or edited
    window.config_saved.connect(
        lambda cid: _register_config_jobs(cid, config_manager, window, _bridges, file_watcher)
    )

    start_minimized = args.minimized_to_tray or settings.start_minimized
    if not start_minimized:
        window.show()

    exit_code = app.exec()
    sched.stop_all()
    file_watcher.stop_all()
    logger.info("CodeSync shut down")
    sys.exit(exit_code)


class _Bridge(QObject):
    """Thread-safe bridge: emit config_id from any thread, delivered on GUI thread."""
    triggered = pyqtSignal(str)


def _register_config_jobs(config_id: str, config_manager: ConfigManager,
                          window, bridges: list, file_watcher: FileWatcher) -> None:
    """Register (or re-register) scheduler/watcher jobs for a single sync config."""
    # Always clean up first so stale jobs don't run when a config is disabled
    sched.stop_jobs_for_config(config_id)
    file_watcher.stop_watch(config_id)

    cfg = config_manager.get_sync_config(config_id)
    if not cfg or not cfg.enabled:
        return
    profile = config_manager.get_profile(cfg.profile_id)
    if not profile or not profile.enabled:
        return

    bridge = _Bridge()
    bridge.triggered.connect(window.trigger_sync_for_config)
    bridges.append(bridge)

    for i, trigger in enumerate(cfg.triggers):
        job_id = f"sync_{cfg.id}_{i}"

        if trigger.type == "interval":
            def _cb(cid=cfg.id, b=bridge):
                b.triggered.emit(cid)
            sched.start_interval(job_id, trigger.interval_seconds, _cb)

        elif trigger.type == "daily":
            def _cb_daily(cid=cfg.id, b=bridge):
                b.triggered.emit(cid)
            sched.start_daily(job_id, trigger.daily_time, _cb_daily)

        elif trigger.type == "watch":
            def _on_change(path: str, cid=cfg.id, b=bridge):
                b.triggered.emit(cid)
            if cfg.local_path:
                file_watcher.start_watch(cfg.id, cfg.local_path, _on_change)


def _start_auto_sync(config_manager: ConfigManager, file_watcher: FileWatcher,
                     window) -> list:
    bridges: list[_Bridge] = []

    for cfg in config_manager.settings.sync_configs:
        if not cfg.enabled:
            continue
        profile = config_manager.get_profile(cfg.profile_id)
        if not profile or not profile.enabled:
            continue

        bridge = _Bridge()
        bridge.triggered.connect(window.trigger_sync_for_config)
        bridges.append(bridge)

        for i, trigger in enumerate(cfg.triggers):
            job_id = f"sync_{cfg.id}_{i}"

            if trigger.type == "interval":
                def _cb(cid=cfg.id, b=bridge):
                    b.triggered.emit(cid)
                sched.start_interval(job_id, trigger.interval_seconds, _cb)

            elif trigger.type == "daily":
                def _cb_daily(cid=cfg.id, b=bridge):
                    b.triggered.emit(cid)
                sched.start_daily(job_id, trigger.daily_time, _cb_daily)

            elif trigger.type == "watch":
                def _on_change(path: str, cid=cfg.id, b=bridge):
                    b.triggered.emit(cid)
                if cfg.local_path:
                    file_watcher.start_watch(cfg.id, cfg.local_path, _on_change)

    return bridges


def _shutdown() -> None:
    QApplication.quit()


if __name__ == "__main__":
    main()
