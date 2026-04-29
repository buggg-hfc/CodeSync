import pytest
from codesync.config.models import ServerProfile, SyncConfig, SyncTrigger
from codesync.config.config_manager import ConfigManager


@pytest.fixture
def tmp_config(tmp_path):
    return ConfigManager(config_file=tmp_path / "config.json")


@pytest.fixture
def sample_profile():
    return ServerProfile(
        id="test-profile-id",
        name="Test Server",
        hostname="192.168.1.100",
        port=22,
        username="testuser",
        auth_type="password",
    )


@pytest.fixture
def sample_sync_config():
    return SyncConfig(
        id="test-config-id",
        profile_id="test-profile-id",
        name="project",
        local_path="/tmp/local/project",
        remote_path="/var/www/project",
        sync_mode="server_to_local",
        triggers=[SyncTrigger(type="interval", interval_seconds=300)],
        exclusion_patterns=[".git/", "*.pyc", "__pycache__/"],
    )
