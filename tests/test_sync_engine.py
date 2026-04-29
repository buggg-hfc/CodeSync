import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from codesync.config.models import ServerProfile, SyncConfig
from codesync.core.ssh_client import FileInfo
from codesync.core.sync_engine import SyncEngine, SyncDiff


@pytest.fixture
def profile():
    return ServerProfile(id="p1", name="Test", hostname="host", username="user")


@pytest.fixture
def sync_config(tmp_path):
    return SyncConfig(
        profile_id="p1",
        local_path=str(tmp_path),
        remote_path="/remote/project",
        sync_mode="server_to_local",
        trigger="manual",
        exclusion_patterns=[],
    )


def test_compute_diff_downloads_new_remote_file():
    engine = SyncEngine()
    remote = {"newfile.py": FileInfo(mtime=1000.0, size=100)}
    local = {}
    diff = engine._compute_diff(remote, local, "server_to_local")
    assert "newfile.py" in diff.to_download
    assert not diff.to_delete_local


def test_compute_diff_deletes_local_file_not_on_server():
    engine = SyncEngine()
    remote = {}
    local = {"old.py": FileInfo(mtime=500.0, size=50)}
    diff = engine._compute_diff(remote, local, "server_to_local")
    assert "old.py" in diff.to_delete_local
    assert "old.py" not in diff.to_download


def test_compute_diff_skips_unchanged_file():
    engine = SyncEngine()
    # Same mtime and size: file is unchanged
    remote = {"same.py": FileInfo(mtime=1000.0, size=200)}
    local = {"same.py": FileInfo(mtime=1000.0, size=200)}
    diff = engine._compute_diff(remote, local, "server_to_local")
    assert "same.py" not in diff.to_download


def test_compute_diff_downloads_newer_remote_file():
    engine = SyncEngine()
    remote = {"updated.py": FileInfo(mtime=2000.0, size=200)}
    local = {"updated.py": FileInfo(mtime=1000.0, size=200)}
    diff = engine._compute_diff(remote, local, "server_to_local")
    assert "updated.py" in diff.to_download


def test_compute_diff_bidirectional_detects_conflict():
    engine = SyncEngine()
    # Both sides are newer than each other (impossible in practice but tests conflict logic)
    remote = {"conflict.py": FileInfo(mtime=2000.0, size=100)}
    local = {"conflict.py": FileInfo(mtime=3000.0, size=100)}
    diff = engine._compute_diff(remote, local, "bidirectional")
    assert "conflict.py" in diff.conflicts
    # Server wins: still downloaded
    assert "conflict.py" in diff.to_download


def test_sync_downloads_file(profile, sync_config, tmp_path):
    engine = SyncEngine()
    mock_client = MagicMock()
    mock_client.list_remote_files.return_value = {
        "src/main.py": FileInfo(mtime=2000.0, size=42)
    }

    progress_calls = []
    summary = engine.sync(profile, sync_config, mock_client, progress_cb=lambda d, t, f: progress_calls.append(f))

    mock_client.download_file.assert_called_once()
    assert summary.files_synced == 1
    assert len(summary.errors) == 0


def test_sync_respects_exclusion_patterns(profile, sync_config, tmp_path):
    sync_config.exclusion_patterns = ["*.pyc"]
    engine = SyncEngine()
    mock_client = MagicMock()
    mock_client.list_remote_files.return_value = {
        "module.py": FileInfo(mtime=2000.0, size=10),
        "module.pyc": FileInfo(mtime=2000.0, size=20),
    }

    summary = engine.sync(profile, sync_config, mock_client)

    # Only module.py should be downloaded
    assert mock_client.download_file.call_count == 1
    call_args = mock_client.download_file.call_args[0]
    assert "module.py" in call_args[0]


def test_crlf_conversion(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_bytes(b"line1\nline2\nline3\n")
    SyncEngine._convert_to_crlf(test_file)
    assert test_file.read_bytes() == b"line1\r\nline2\r\nline3\r\n"


def test_crlf_conversion_skips_binary(tmp_path):
    test_file = tmp_path / "data.bin"
    binary_data = b"\x00\x01\x02\x03\n\x04\x05"
    test_file.write_bytes(binary_data)
    SyncEngine._convert_to_crlf(test_file)
    assert test_file.read_bytes() == binary_data  # unchanged
