import os
from pathlib import Path

APP_NAME = "CodeSync"
APP_VERSION = "0.1.0"

# Config directory: %APPDATA%\codesync on Windows, ~/.config/codesync elsewhere
_appdata = os.environ.get("APPDATA")
if _appdata:
    CONFIG_DIR = Path(_appdata) / "codesync"
else:
    CONFIG_DIR = Path.home() / ".config" / "codesync"

CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = CONFIG_DIR / "codesync.log"

DEFAULT_SYNC_INTERVAL = 300  # seconds
DEFAULT_SSH_PORT = 22
MAX_LOG_LINES = 1000
LOG_ROTATE_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_ROTATE_COUNT = 3

DEFAULT_EXCLUSION_PATTERNS = [
    ".git/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "node_modules/",
    ".env",
    "*.log",
    ".DS_Store",
    "Thumbs.db",
]
