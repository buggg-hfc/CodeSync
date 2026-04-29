from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from pathlib import PurePosixPath


@dataclass
class SyncTrigger:
    type: str = "manual"        # "manual" | "interval" | "daily"
    interval_seconds: int = 300
    daily_time: str = "02:00"  # HH:MM for daily type


@dataclass
class SyncConfig:
    profile_id: str
    local_path: str    # actual sync target directory (parent/remote_name)
    remote_path: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    sync_mode: str = "server_to_local"   # | "bidirectional"
    triggers: list[SyncTrigger] = field(default_factory=list)
    exclusion_patterns: list[str] = field(default_factory=list)
    max_file_size_mb: int = 0   # 0 = no limit; files larger than this are skipped
    line_ending: str = "keep"   # "keep" | "crlf"
    delete_removed_files: bool = True   # delete local files when removed from server
    enabled: bool = True

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.name and self.remote_path:
            self.name = PurePosixPath(self.remote_path).name or self.remote_path


@dataclass
class ServerProfile:
    name: str
    hostname: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    port: int = 22
    username: str = ""
    auth_type: str = "password"  # "password" | "key"
    key_path: str = ""
    enabled: bool = True

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class AppSettings:
    version: int = 2
    profiles: list[ServerProfile] = field(default_factory=list)
    sync_configs: list[SyncConfig] = field(default_factory=list)
    start_minimized: bool = False
    show_notifications: bool = True
    log_level: str = "INFO"
    font_size: int = 14
