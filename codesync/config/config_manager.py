from __future__ import annotations
import json
import os
from pathlib import Path

try:
    import keyring
    _KEYRING_AVAILABLE = True
except ImportError:
    _KEYRING_AVAILABLE = False

from codesync.config.models import AppSettings, ServerProfile, SyncConfig, SyncTrigger
from codesync.utils.constants import CONFIG_DIR, CONFIG_FILE

_KEYRING_SERVICE = "codesync"
_SCHEMA_VERSION = 2


# ── Serialisation helpers ──────────────────────────────────────────────────────

def _trigger_to_dict(t: SyncTrigger) -> dict:
    return {"type": t.type, "interval_seconds": t.interval_seconds, "daily_time": t.daily_time}


def _trigger_from_dict(d: dict) -> SyncTrigger:
    return SyncTrigger(
        type=d.get("type", "manual"),
        interval_seconds=d.get("interval_seconds", 300),
        daily_time=d.get("daily_time", "02:00"),
    )


def _profile_to_dict(p: ServerProfile) -> dict:
    return {
        "id": p.id, "name": p.name, "hostname": p.hostname, "port": p.port,
        "username": p.username, "auth_type": p.auth_type, "key_path": p.key_path,
        "enabled": p.enabled,
    }


def _profile_from_dict(d: dict) -> ServerProfile:
    return ServerProfile(
        id=d.get("id", ""), name=d.get("name", ""), hostname=d.get("hostname", ""),
        port=d.get("port", 22), username=d.get("username", ""),
        auth_type=d.get("auth_type", "password"), key_path=d.get("key_path", ""),
        enabled=d.get("enabled", True),
    )


def _sync_config_to_dict(c: SyncConfig) -> dict:
    return {
        "id": c.id, "profile_id": c.profile_id, "name": c.name,
        "local_path": c.local_path, "remote_path": c.remote_path,
        "sync_mode": c.sync_mode, "triggers": [_trigger_to_dict(t) for t in c.triggers],
        "exclusion_patterns": c.exclusion_patterns, "max_file_size_mb": c.max_file_size_mb,
        "line_ending": c.line_ending, "delete_removed_files": c.delete_removed_files,
        "enabled": c.enabled,
    }


def _sync_config_from_dict(d: dict) -> SyncConfig:
    # Migrate v1 format: single trigger string → triggers list
    if "triggers" in d:
        triggers = [_trigger_from_dict(t) for t in d["triggers"]]
    else:
        old_trigger = d.get("trigger", "manual")
        interval = d.get("interval_seconds", 300)
        if old_trigger == "manual":
            triggers = [SyncTrigger(type="manual")]
        elif old_trigger == "interval":
            triggers = [SyncTrigger(type="interval", interval_seconds=interval)]
        elif old_trigger == "watch":
            triggers = [SyncTrigger(type="watch")]
        else:
            triggers = [SyncTrigger(type="manual")]

    return SyncConfig(
        id=d.get("id", ""),
        profile_id=d.get("profile_id", ""),
        name=d.get("name", ""),
        local_path=d.get("local_path", ""),
        remote_path=d.get("remote_path", ""),
        sync_mode=d.get("sync_mode", "server_to_local"),
        triggers=triggers,
        exclusion_patterns=d.get("exclusion_patterns", []),
        max_file_size_mb=d.get("max_file_size_mb", 0),
        line_ending=d.get("line_ending", "keep"),
        delete_removed_files=d.get("delete_removed_files", True),
        enabled=d.get("enabled", True),
    )


# ── ConfigManager ──────────────────────────────────────────────────────────────

class ConfigManager:
    def __init__(self, config_file: Path = CONFIG_FILE):
        self._config_file = config_file
        self._settings: AppSettings | None = None

    def load(self) -> AppSettings:
        if not self._config_file.exists():
            self._settings = AppSettings()
            return self._settings

        with open(self._config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        profiles = [_profile_from_dict(p) for p in data.get("profiles", [])]
        sync_configs = [_sync_config_from_dict(c) for c in data.get("sync_configs", [])]
        self._settings = AppSettings(
            version=data.get("version", 1),
            profiles=profiles,
            sync_configs=sync_configs,
            start_minimized=data.get("start_minimized", False),
            show_notifications=data.get("show_notifications", True),
            log_level=data.get("log_level", "INFO"),
            font_size=data.get("font_size", 10),
        )
        return self._settings

    def save(self, settings: AppSettings | None = None) -> None:
        if settings is not None:
            self._settings = settings
        if self._settings is None:
            return

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "version": _SCHEMA_VERSION,
            "start_minimized": self._settings.start_minimized,
            "show_notifications": self._settings.show_notifications,
            "log_level": self._settings.log_level,
            "font_size": self._settings.font_size,
            "profiles": [_profile_to_dict(p) for p in self._settings.profiles],
            "sync_configs": [_sync_config_to_dict(c) for c in self._settings.sync_configs],
        }
        tmp_path = self._config_file.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self._config_file)

    @property
    def settings(self) -> AppSettings:
        if self._settings is None:
            self.load()
        return self._settings

    # ── Profile helpers ────────────────────────────────────────────────────

    def add_profile(self, profile: ServerProfile) -> None:
        self.settings.profiles.append(profile)
        self.save()

    def update_profile(self, profile: ServerProfile) -> None:
        for i, p in enumerate(self.settings.profiles):
            if p.id == profile.id:
                self.settings.profiles[i] = profile
                self.save()
                return

    def delete_profile(self, profile_id: str) -> None:
        self.settings.profiles = [p for p in self.settings.profiles if p.id != profile_id]
        self.settings.sync_configs = [c for c in self.settings.sync_configs if c.profile_id != profile_id]
        self.save()

    def get_profile(self, profile_id: str) -> ServerProfile | None:
        for p in self.settings.profiles:
            if p.id == profile_id:
                return p
        return None

    # ── SyncConfig helpers ─────────────────────────────────────────────────

    def get_sync_configs_for_profile(self, profile_id: str) -> list[SyncConfig]:
        return [c for c in self.settings.sync_configs if c.profile_id == profile_id]

    def get_sync_config(self, config_id: str) -> SyncConfig | None:
        for c in self.settings.sync_configs:
            if c.id == config_id:
                return c
        return None

    def save_sync_config(self, config: SyncConfig) -> None:
        for i, c in enumerate(self.settings.sync_configs):
            if c.id == config.id:
                self.settings.sync_configs[i] = config
                self.save()
                return
        self.settings.sync_configs.append(config)
        self.save()

    def delete_sync_config(self, config_id: str) -> None:
        self.settings.sync_configs = [c for c in self.settings.sync_configs if c.id != config_id]
        self.save()

    # ── Credential helpers (keyring) ───────────────────────────────────────

    def save_credential(self, profile_id: str, key: str, value: str) -> None:
        if not _KEYRING_AVAILABLE or not value:
            return
        keyring.set_password(_KEYRING_SERVICE, f"{profile_id}:{key}", value)

    def load_credential(self, profile_id: str, key: str) -> str:
        if not _KEYRING_AVAILABLE:
            return ""
        return keyring.get_password(_KEYRING_SERVICE, f"{profile_id}:{key}") or ""

    def delete_credential(self, profile_id: str, key: str) -> None:
        if not _KEYRING_AVAILABLE:
            return
        try:
            keyring.delete_password(_KEYRING_SERVICE, f"{profile_id}:{key}")
        except Exception:
            pass
