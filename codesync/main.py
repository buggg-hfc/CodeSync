from __future__ import annotations
import sys
import argparse

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal

from codesync.utils.constants import APP_NAME
from codesync.utils.logger import setup_logging, logger
from codesync.config.config_manager import ConfigManager
from codesync.core import scheduler as sched
from codesync.core.file_watcher import FileWatcher


def main() -> None:
    parser = argparse.ArgumentParser(prog="codesync")
    parser.add_argument("--minimized-to-tray", action="store_true", help="Start minimized to system tray")
    args, qt_args = parser.parse_known_args()

    app = QApplication(sys.argv[:1] + qt_args)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    config_manager = ConfigManager()
    settings = config_manager.load()
    setup_logging(settings.log_level)
    logger.info("CodeSync starting up")

    from codesync.gui.main_window import MainWindow
    from codesync.gui.tray_icon import TrayIcon

    window = MainWindow(config_manager)
    tray = TrayIcon(config_manager)
    tray.setVisible(True)

    # Wire tray signals
    tray.open_requested.connect(window.show)
    tray.open_requested.connect(window.raise_)
    tray.quit_requested.connect(_shutdown)
    window.closed.connect(_shutdown)

    def _sync_from_tray(profile_id: str) -> None:
        profile = config_manager.get_profile(profile_id)
        config = config_manager.get_sync_config(profile_id)
        if profile and config:
            window.show()
            window.raise_()
            # Delegate to sync tab
            window._sync_tab.set_profile(profile)
            window._sync_tab._start_sync()

    tray.sync_now_requested.connect(_sync_from_tray)

    # Start auto-sync for enabled interval-based profiles.
    # Keep bridges alive for the entire app lifetime.
    file_watcher = FileWatcher()
    _auto_sync_bridges = _start_auto_sync(config_manager, file_watcher, window, tray)

    start_minimized = args.minimized_to_tray or settings.start_minimized
    if not start_minimized:
        window.show()

    exit_code = app.exec()

    sched.stop_all()
    file_watcher.stop_all()
    logger.info("CodeSync shut down")
    sys.exit(exit_code)


class _AutoSyncBridge(QObject):
    """Emits a signal from any thread; Qt delivers it on the GUI thread."""
    triggered = pyqtSignal(str)   # profile_id


def _start_auto_sync(config_manager: ConfigManager, file_watcher: FileWatcher, window, tray) -> list:
    """Activate auto-sync for all enabled profiles on startup.

    Returns the list of bridge objects — callers must keep a reference so the
    bridges are not garbage-collected while the app is running.
    """
    bridges: list[_AutoSyncBridge] = []

    for cfg in config_manager.settings.sync_configs:
        if not cfg.enabled:
            continue
        profile = config_manager.get_profile(cfg.profile_id)
        if not profile:
            continue

        if cfg.trigger == "interval":
            bridge = _AutoSyncBridge()
            # QueuedConnection is implicit when connecting across threads
            bridge.triggered.connect(window.trigger_sync_for_profile)
            bridges.append(bridge)

            def _callback(pid=profile.id, b=bridge):
                b.triggered.emit(pid)

            sched.start_interval(cfg.profile_id, cfg.interval_seconds, _callback)

        elif cfg.trigger == "watch":
            bridge = _AutoSyncBridge()
            bridge.triggered.connect(window.trigger_sync_for_profile)
            bridges.append(bridge)

            def _on_change(path: str, pid=profile.id, b=bridge):
                b.triggered.emit(pid)

            if cfg.local_path:
                file_watcher.start_watch(cfg.profile_id, cfg.local_path, _on_change)

    return bridges


def _shutdown() -> None:
    from PyQt6.QtWidgets import QApplication
    QApplication.quit()


if __name__ == "__main__":
    main()
