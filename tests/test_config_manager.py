import pytest
from codesync.config.models import ServerProfile, SyncConfig
from codesync.config.config_manager import ConfigManager


def test_save_and_load_roundtrip(tmp_config, sample_profile, sample_sync_config):
    tmp_config.add_profile(sample_profile)
    tmp_config.save_sync_config(sample_sync_config)

    # Reload from disk
    fresh = ConfigManager(tmp_config._config_file)
    settings = fresh.load()

    assert len(settings.profiles) == 1
    p = settings.profiles[0]
    assert p.id == sample_profile.id
    assert p.name == sample_profile.name
    assert p.hostname == sample_profile.hostname
    assert p.port == 22

    assert len(settings.sync_configs) == 1
    c = settings.sync_configs[0]
    assert c.local_path == sample_sync_config.local_path
    assert c.remote_path == sample_sync_config.remote_path
    assert ".git/" in c.exclusion_patterns


def test_delete_profile_also_removes_sync_config(tmp_config, sample_profile, sample_sync_config):
    tmp_config.add_profile(sample_profile)
    tmp_config.save_sync_config(sample_sync_config)
    tmp_config.delete_profile(sample_profile.id)

    assert tmp_config.get_profile(sample_profile.id) is None
    assert tmp_config.get_sync_config(sample_profile.id) is None


def test_update_profile(tmp_config, sample_profile):
    tmp_config.add_profile(sample_profile)
    updated = ServerProfile(
        id=sample_profile.id,
        name="Updated Name",
        hostname="10.0.0.1",
        port=2222,
        username="root",
    )
    tmp_config.update_profile(updated)

    p = tmp_config.get_profile(sample_profile.id)
    assert p.name == "Updated Name"
    assert p.hostname == "10.0.0.1"
    assert p.port == 2222


def test_atomic_write_creates_no_tmp_on_success(tmp_config, sample_profile):
    tmp_config.add_profile(sample_profile)
    tmp_file = tmp_config._config_file.with_suffix(".json.tmp")
    assert not tmp_file.exists(), "Temp file should be cleaned up after atomic write"


def test_load_returns_empty_settings_when_no_file(tmp_config):
    settings = tmp_config.load()
    assert settings.profiles == []
    assert settings.sync_configs == []
    assert settings.version == 1
