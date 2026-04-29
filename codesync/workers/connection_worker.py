from PyQt6.QtCore import QThread, pyqtSignal

from codesync.config.models import ServerProfile
from codesync.core.ssh_client import SSHClient


class ConnectionWorker(QThread):
    success = pyqtSignal()
    failure = pyqtSignal(str)

    def __init__(self, profile: ServerProfile, password: str = "", passphrase: str = ""):
        super().__init__()
        self._profile = profile
        self._password = password
        self._passphrase = passphrase

    def run(self) -> None:
        ok, msg = SSHClient.test_connection(self._profile, self._password, self._passphrase)
        if ok:
            self.success.emit()
        else:
            self.failure.emit(msg)
