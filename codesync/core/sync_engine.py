from __future__ import annotations
import os
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable

from codesync.config.models import ServerProfile, SyncConfig
from codesync.core.exclusion_filter import ExclusionFilter
from codesync.core.ssh_client import FileInfo, SSHClient
from codesync.utils.logger import logger

ProgressCallback = Callable[[int, int, str], None]  # (done, total, current_file)


@dataclass
class SyncDiff:
    to_download: list[str] = field(default_factory=list)   # relative paths
    to_delete_local: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


@dataclass
class SyncSummary:
    files_synced: int = 0
    files_skipped: int = 0
    files_deleted: int = 0
    conflicts: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)


class SyncEngine:
    def sync(
        self,
        profile: ServerProfile,
        config: SyncConfig,
        client: SSHClient,
        progress_cb: ProgressCallback | None = None,
        stop_flag: Callable[[], bool] | None = None,
    ) -> SyncSummary:
        start = time.monotonic()
        summary = SyncSummary()

        excl = ExclusionFilter(config.exclusion_patterns)
        local_base = Path(config.local_path)

        logger.info("Starting sync: %s -> %s", config.remote_path, config.local_path)

        # 1. Gather remote file list
        try:
            remote_files = client.list_remote_files(config.remote_path)
        except Exception as e:
            summary.errors.append(f"Failed to list remote files: {e}")
            logger.error("List remote failed: %s", e)
            return summary

        # 2. Filter excluded files and oversized files
        max_bytes = config.max_file_size_mb * 1024 * 1024 if config.max_file_size_mb > 0 else 0
        remote_files = {
            k: v for k, v in remote_files.items()
            if not excl.is_excluded(k) and (max_bytes == 0 or v.size <= max_bytes)
        }

        # 3. Gather local file list
        local_files = self._list_local_files(local_base, excl)

        # 4. Compute diff
        diff = self._compute_diff(remote_files, local_files, config.sync_mode)
        summary.conflicts = len(diff.conflicts)

        total = len(diff.to_download) + len(diff.to_delete_local)
        done = 0

        # 5. Download files from server
        for rel_path in diff.to_download:
            if stop_flag and stop_flag():
                logger.info("Sync cancelled by user")
                break

            remote_full = config.remote_path.rstrip("/") + "/" + rel_path
            # Convert POSIX relative path to local OS path
            local_path = local_base / Path(*PurePosixPath(rel_path).parts)

            if progress_cb:
                progress_cb(done, total, rel_path)

            try:
                client.download_file(remote_full, local_path)
                # Apply line ending conversion if requested
                if config.line_ending == "crlf":
                    self._convert_to_crlf(local_path)
                summary.files_synced += 1
                logger.debug("Downloaded: %s", rel_path)
            except Exception as e:
                summary.errors.append(f"{rel_path}: {e}")
                logger.warning("Download failed %s: %s", rel_path, e)
            done += 1

        # 6. Delete local files that no longer exist on server (server→local mode)
        for rel_path in diff.to_delete_local:
            if stop_flag and stop_flag():
                break
            local_path = local_base / Path(*PurePosixPath(rel_path).parts)
            try:
                local_path.unlink(missing_ok=True)
                summary.files_deleted += 1
                logger.debug("Deleted local: %s", rel_path)
            except Exception as e:
                summary.errors.append(f"delete {rel_path}: {e}")
            done += 1
            if progress_cb:
                progress_cb(done, total, rel_path)

        if progress_cb:
            progress_cb(total, total, "")

        summary.files_skipped = len(remote_files) - summary.files_synced
        summary.duration_seconds = time.monotonic() - start
        summary.timestamp = time.time()
        logger.info(
            "Sync complete: %d synced, %d skipped, %d deleted, %d errors in %.1fs",
            summary.files_synced,
            summary.files_skipped,
            summary.files_deleted,
            len(summary.errors),
            summary.duration_seconds,
        )
        return summary

    # ── Internal helpers ──────────────────────────────────────────────────

    def _list_local_files(self, base: Path, excl: ExclusionFilter) -> dict[str, FileInfo]:
        result: dict[str, FileInfo] = {}
        if not base.exists():
            return result
        for dirpath, dirnames, filenames in os.walk(base):
            # Prune excluded directories in-place
            dirnames[:] = [
                d for d in dirnames
                if not excl.is_excluded(
                    (Path(dirpath) / d).relative_to(base).as_posix() + "/"
                )
            ]
            for fname in filenames:
                full = Path(dirpath) / fname
                rel = full.relative_to(base).as_posix()
                if excl.is_excluded(rel):
                    continue
                st = full.stat()
                result[rel] = FileInfo(mtime=st.st_mtime, size=st.st_size)
        return result

    def _compute_diff(
        self,
        remote: dict[str, FileInfo],
        local: dict[str, FileInfo],
        sync_mode: str,
    ) -> SyncDiff:
        diff = SyncDiff()
        for rel, rinfo in remote.items():
            if rel not in local:
                diff.to_download.append(rel)
            else:
                linfo = local[rel]
                remote_newer = rinfo.mtime > linfo.mtime + 1
                local_newer = linfo.mtime > rinfo.mtime + 1
                size_changed = rinfo.size != linfo.size

                if sync_mode == "bidirectional" and local_newer:
                    # Local was modified after the server — conflict, server wins
                    diff.conflicts.append(rel)
                    diff.to_download.append(rel)
                elif remote_newer or size_changed:
                    diff.to_download.append(rel)

        if sync_mode == "server_to_local":
            for rel in local:
                if rel not in remote:
                    diff.to_delete_local.append(rel)

        return diff

    @staticmethod
    def _convert_to_crlf(path: Path) -> None:
        """Convert LF to CRLF in a text file. Skips binary files silently."""
        try:
            data = path.read_bytes()
            if b"\x00" in data:
                return  # binary file, skip
            text = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            path.write_bytes(text)
        except Exception:
            pass
