from __future__ import annotations
import stat
import os
from dataclasses import dataclass
from pathlib import PurePosixPath, Path
from typing import Callable

import paramiko

from codesync.config.models import ServerProfile
from codesync.utils.logger import logger


@dataclass
class FileInfo:
    mtime: float
    size: int


class SSHClient:
    """Manages an SSH/SFTP connection to a single server profile."""

    def __init__(self):
        self._ssh: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None
        self._connected = False

    # ── Connection lifecycle ───────────────────────────────────────────────

    def connect(self, profile: ServerProfile, password: str = "", key_passphrase: str = "") -> None:
        self.disconnect()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs: dict = {
            "hostname": profile.hostname,
            "port": profile.port,
            "username": profile.username,
            "timeout": 15,
        }

        if profile.auth_type == "key" and profile.key_path:
            key_path = str(Path(profile.key_path).expanduser())
            connect_kwargs["key_filename"] = key_path
            if key_passphrase:
                connect_kwargs["passphrase"] = key_passphrase
        else:
            connect_kwargs["password"] = password

        client.connect(**connect_kwargs)
        self._ssh = client
        self._sftp = client.open_sftp()
        self._connected = True
        logger.info("Connected to %s:%d as %s", profile.hostname, profile.port, profile.username)

    def disconnect(self) -> None:
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None
        if self._ssh:
            try:
                self._ssh.close()
            except Exception:
                pass
            self._ssh = None
        self._connected = False

    def is_connected(self) -> bool:
        if not self._connected or self._ssh is None:
            return False
        transport = self._ssh.get_transport()
        return transport is not None and transport.is_active()

    @staticmethod
    def test_connection(profile: ServerProfile, password: str = "", key_passphrase: str = "") -> tuple[bool, str]:
        """Attempt a connection and immediately close it. Returns (ok, message)."""
        client = SSHClient()
        try:
            client.connect(profile, password=password, key_passphrase=key_passphrase)
            client.disconnect()
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)
        finally:
            client.disconnect()

    # ── Remote file listing ────────────────────────────────────────────────

    def list_remote_files(self, remote_path: str) -> dict[str, FileInfo]:
        """Recursively list all files under remote_path.

        Returns a dict mapping relative POSIX paths to FileInfo.
        """
        assert self._sftp is not None, "Not connected"
        result: dict[str, FileInfo] = {}
        self._walk_remote(remote_path, remote_path, result)
        return result

    def _walk_remote(self, base: str, current: str, result: dict) -> None:
        assert self._sftp is not None
        try:
            entries = self._sftp.listdir_attr(current)
        except IOError as e:
            logger.warning("Cannot list remote dir %s: %s", current, e)
            return

        for entry in entries:
            remote_full = current.rstrip("/") + "/" + entry.filename
            if stat.S_ISDIR(entry.st_mode or 0):
                self._walk_remote(base, remote_full, result)
            else:
                rel = remote_full[len(base):].lstrip("/")
                result[rel] = FileInfo(
                    mtime=float(entry.st_mtime or 0),
                    size=int(entry.st_size or 0),
                )

    # ── File transfer ─────────────────────────────────────────────────────

    def download_file(
        self,
        remote_path: str,
        local_path: Path,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> None:
        assert self._sftp is not None, "Not connected"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._sftp.get(remote_path, str(local_path), callback=progress_cb)

    def upload_file(self, local_path: Path, remote_path: str) -> None:
        assert self._sftp is not None, "Not connected"
        # Ensure remote parent directory exists
        remote_dir = str(PurePosixPath(remote_path).parent)
        self._mkdir_remote(remote_dir)
        self._sftp.put(str(local_path), remote_path)

    def _mkdir_remote(self, remote_dir: str) -> None:
        assert self._sftp is not None
        parts = PurePosixPath(remote_dir).parts
        path = ""
        for part in parts:
            path = path + "/" + part if path else part
            if not path.startswith("/"):
                path = "/" + path
            try:
                self._sftp.stat(path)
            except IOError:
                try:
                    self._sftp.mkdir(path)
                except IOError:
                    pass
