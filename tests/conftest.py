import pytest
import tempfile
from pathlib import Path

from codesync.config.models import ServerProfile, SyncConfig, AppSettings
from codesync.config.config_manager import ConfigManager


@pytest.fixture
def tmp_config(tmp_path):
    config_file = tmp_path / "config.json"
    return ConfigManager(config_file=config_file)


@pytest.fixture
def sample_profile():
    return ServerProfile(
        id="test-profile-id",
        name="Test Server",
        hostname="192.168.1.100",
        port=22,
        username="testuser",
        auth_type="key",
        key_path="/home/user/.ssh/id_ed25519",
    )


@pytest.fixture
def sample_sync_config():
    return SyncConfig(
        profile_id="test-profile-id",
        local_path="/tmp/local",
        remote_path="/var/www/project",
        sync_mode="server_to_local",
        trigger="manual",
        interval_seconds=300,
        exclusion_patterns=[".git/", "*.pyc", "__pycache__/"],
    )
