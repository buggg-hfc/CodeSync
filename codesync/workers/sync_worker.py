from __future__ import annotations
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from codesync.config.models import ServerProfile, SyncConfig
from codesync.config.config_manager import ConfigManager
from codesync.core.ssh_client import SSHClient
from codesync.core.sync_engine import SyncEngine, SyncSummary
from codesync.utils.logger import logger


class SyncWorker(QThread):
    progress = pyqtSignal(int, int, str)   # done, total, current_file
    finished = pyqtSignal(object)           # SyncSummary
    error = pyqtSignal(str)

    def __init__(self, profile: ServerProfile, config: SyncConfig, config_manager: ConfigManager):
        super().__init__()
        self._profile = profile
        self._config = config
        self._config_manager = config_manager
        self._stop_event = threading.Event()

    def request_stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        client = SSHClient()
        try:
            password = self._config_manager.load_credential(self._profile.id, "password")
            passphrase = self._config_manager.load_credential(self._profile.id, "passphrase")
            client.connect(self._profile, password=password, key_passphrase=passphrase)
        except Exception as e:
            logger.error("Connection failed: %s", e)
            self.error.emit(f"连接失败：{e}")
            return

        def _progress(done: int, total: int, filename: str) -> None:
            self.progress.emit(done, total, filename)

        engine = SyncEngine()
        try:
            summary: SyncSummary = engine.sync(
                self._profile,
                self._config,
                client,
                progress_cb=_progress,
                stop_flag=self._stop_event.is_set,
            )
            self.finished.emit(summary)
        except Exception as e:
            logger.error("Sync error: %s", e)
            self.error.emit(f"同步出错：{e}")
        finally:
            client.disconnect()
