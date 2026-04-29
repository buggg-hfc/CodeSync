import pytest
from codesync.config.models import ServerProfile, SyncConfig, SyncTrigger
from codesync.config.config_manager import ConfigManager


def test_save_and_load_roundtrip(tmp_config, sample_profile, sample_sync_config):
    tmp_config.add_profile(sample_profile)
    tmp_config.save_sync_config(sample_sync_config)

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
    assert c.id == sample_sync_config.id
    assert c.local_path == sample_sync_config.local_path
    assert c.remote_path == sample_sync_config.remote_path
    assert len(c.triggers) == 1
    assert c.triggers[0].type == "interval"
    assert c.triggers[0].interval_seconds == 300
    assert ".git/" in c.exclusion_patterns


def test_delete_profile_also_removes_sync_config(tmp_config, sample_profile, sample_sync_config):
    tmp_config.add_profile(sample_profile)
    tmp_config.save_sync_config(sample_sync_config)
    tmp_config.delete_profile(sample_profile.id)

    assert tmp_config.get_profile(sample_profile.id) is None
    assert tmp_config.get_sync_config(sample_sync_config.id) is None


def test_multiple_sync_configs_per_profile(tmp_config, sample_profile):
    tmp_config.add_profile(sample_profile)
    c1 = SyncConfig(
        profile_id=sample_profile.id,
        local_path="/tmp/proj1",
        remote_path="/home/user/proj1",
        triggers=[SyncTrigger(type="manual")],
    )
    c2 = SyncConfig(
        profile_id=sample_profile.id,
        local_path="/tmp/proj2",
        remote_path="/home/user/proj2",
        triggers=[SyncTrigger(type="daily", daily_time="03:00")],
    )
    tmp_config.save_sync_config(c1)
    tmp_config.save_sync_config(c2)

    cfgs = tmp_config.get_sync_configs_for_profile(sample_profile.id)
    assert len(cfgs) == 2

    fresh = ConfigManager(tmp_config._config_file)
    fresh.load()
    assert len(fresh.get_sync_configs_for_profile(sample_profile.id)) == 2


def test_update_profile(tmp_config, sample_profile):
    tmp_config.add_profile(sample_profile)
    updated = ServerProfile(
        id=sample_profile.id,
        name="Updated",
        hostname="10.0.0.1",
        port=2222,
        username="root",
    )
    tmp_config.update_profile(updated)
    p = tmp_config.get_profile(sample_profile.id)
    assert p.name == "Updated"
    assert p.port == 2222


def test_atomic_write_no_tmp(tmp_config, sample_profile):
    tmp_config.add_profile(sample_profile)
    assert not tmp_config._config_file.with_suffix(".json.tmp").exists()


def test_v1_migration(tmp_path):
    """Config files written in v1 format (trigger string) should migrate cleanly."""
    import json
    v1_data = {
        "version": 1,
        "profiles": [{"id": "p1", "name": "Old", "hostname": "host",
                      "port": 22, "username": "u", "auth_type": "key", "key_path": ""}],
        "sync_configs": [{
            "profile_id": "p1",
            "local_path": "/tmp/x",
            "remote_path": "/remote/x",
            "sync_mode": "server_to_local",
            "trigger": "interval",
            "interval_seconds": 120,
            "exclusion_patterns": [],
            "line_ending": "keep",
            "enabled": True,
        }],
        "start_minimized": False,
        "show_notifications": True,
        "log_level": "INFO",
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(v1_data), encoding="utf-8")

    mgr = ConfigManager(cfg_file)
    settings = mgr.load()

    assert len(settings.sync_configs) == 1
    c = settings.sync_configs[0]
    assert len(c.triggers) == 1
    assert c.triggers[0].type == "interval"
    assert c.triggers[0].interval_seconds == 120
