from __future__ import annotations
import uuid
from dataclasses import dataclass, field


@dataclass
class ServerProfile:
    name: str
    hostname: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    port: int = 22
    username: str = ""
    auth_type: str = "key"       # "password" | "key"
    key_path: str = ""
    # Passwords and passphrases are stored in the OS keyring, not here.

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class SyncConfig:
    profile_id: str
    local_path: str
    remote_path: str
    sync_mode: str = "server_to_local"   # | "bidirectional"
    trigger: str = "manual"              # | "interval" | "watch"
    interval_seconds: int = 300
    exclusion_patterns: list[str] = field(default_factory=list)
    line_ending: str = "keep"            # "keep" | "crlf"
    enabled: bool = True


@dataclass
class AppSettings:
    version: int = 1
    profiles: list[ServerProfile] = field(default_factory=list)
    sync_configs: list[SyncConfig] = field(default_factory=list)
    start_minimized: bool = False
    show_notifications: bool = True
    log_level: str = "INFO"
