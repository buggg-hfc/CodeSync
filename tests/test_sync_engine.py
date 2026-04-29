import pytest
from pathlib import Path
from unittest.mock import MagicMock

from codesync.config.models import ServerProfile, SyncConfig, SyncTrigger
from codesync.core.ssh_client import FileInfo
from codesync.core.sync_engine import SyncEngine


@pytest.fixture
def profile():
    return ServerProfile(id="p1", name="Test", hostname="host", username="user")


@pytest.fixture
def sync_config(tmp_path):
    return SyncConfig(
        id="c1",
        profile_id="p1",
        local_path=str(tmp_path),
        remote_path="/remote/project",
        sync_mode="server_to_local",
        triggers=[SyncTrigger(type="manual")],
        exclusion_patterns=[],
        max_file_size_mb=0,
    )


def test_compute_diff_downloads_new_remote_file():
    engine = SyncEngine()
    remote = {"newfile.py": FileInfo(mtime=1000.0, size=100)}
    diff = engine._compute_diff(remote, {}, "server_to_local")
    assert "newfile.py" in diff.to_download


def test_compute_diff_deletes_local_file_not_on_server():
    engine = SyncEngine()
    local = {"old.py": FileInfo(mtime=500.0, size=50)}
    diff = engine._compute_diff({}, local, "server_to_local")
    assert "old.py" in diff.to_delete_local


def test_compute_diff_skips_unchanged_file():
    engine = SyncEngine()
    info = FileInfo(mtime=1000.0, size=200)
    diff = engine._compute_diff({"same.py": info}, {"same.py": info}, "server_to_local")
    assert "same.py" not in diff.to_download


def test_compute_diff_downloads_newer_remote():
    engine = SyncEngine()
    diff = engine._compute_diff(
        {"f.py": FileInfo(mtime=2000.0, size=200)},
        {"f.py": FileInfo(mtime=1000.0, size=200)},
        "server_to_local",
    )
    assert "f.py" in diff.to_download


def test_compute_diff_bidirectional_conflict():
    engine = SyncEngine()
    diff = engine._compute_diff(
        {"c.py": FileInfo(mtime=2000.0, size=100)},
        {"c.py": FileInfo(mtime=3000.0, size=100)},
        "bidirectional",
    )
    assert "c.py" in diff.conflicts
    assert "c.py" in diff.to_download


def test_sync_downloads_file(profile, sync_config, tmp_path):
    engine = SyncEngine()
    mock_client = MagicMock()
    mock_client.list_remote_files.return_value = {
        "src/main.py": FileInfo(mtime=2000.0, size=42)
    }
    summary = engine.sync(profile, sync_config, mock_client)
    mock_client.download_file.assert_called_once()
    assert summary.files_synced == 1


def test_sync_respects_exclusion_patterns(profile, sync_config, tmp_path):
    sync_config.exclusion_patterns = ["*.pyc"]
    engine = SyncEngine()
    mock_client = MagicMock()
    mock_client.list_remote_files.return_value = {
        "module.py": FileInfo(mtime=2000.0, size=10),
        "module.pyc": FileInfo(mtime=2000.0, size=20),
    }
    engine.sync(profile, sync_config, mock_client)
    assert mock_client.download_file.call_count == 1
    call_args = mock_client.download_file.call_args[0]
    assert "module.py" in call_args[0]


def test_sync_respects_max_file_size(profile, sync_config):
    sync_config.max_file_size_mb = 1  # 1 MB limit
    engine = SyncEngine()
    mock_client = MagicMock()
    mock_client.list_remote_files.return_value = {
        "small.py": FileInfo(mtime=2000.0, size=100),
        "large.bin": FileInfo(mtime=2000.0, size=2 * 1024 * 1024),  # 2 MB
    }
    engine.sync(profile, sync_config, mock_client)
    assert mock_client.download_file.call_count == 1
    call_args = mock_client.download_file.call_args[0]
    assert "small.py" in call_args[0]


def test_crlf_conversion(tmp_path):
    f = tmp_path / "test.py"
    f.write_bytes(b"line1\nline2\n")
    SyncEngine._convert_to_crlf(f)
    assert f.read_bytes() == b"line1\r\nline2\r\n"


def test_crlf_skips_binary(tmp_path):
    f = tmp_path / "data.bin"
    data = b"\x00\x01\x02\n"
    f.write_bytes(data)
    SyncEngine._convert_to_crlf(f)
    assert f.read_bytes() == data
