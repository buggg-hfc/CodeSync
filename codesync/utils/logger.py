import logging
import logging.handlers
from collections import deque

from codesync.utils.constants import CONFIG_DIR, LOG_FILE, MAX_LOG_LINES, LOG_ROTATE_BYTES, LOG_ROTATE_COUNT

# Qt bridge is set up lazily to avoid importing Qt in non-GUI contexts
_qt_bridge = None


class RingBufferHandler(logging.Handler):
    """In-memory ring buffer that keeps the last N log records."""

    def __init__(self, maxlen: int = MAX_LOG_LINES):
        super().__init__()
        self._buffer: deque = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self._buffer.append(msg)
        if _qt_bridge is not None:
            try:
                _qt_bridge.new_log_line.emit(msg)
            except Exception:
                pass

    def get_lines(self) -> list[str]:
        return list(self._buffer)


_ring_handler = RingBufferHandler()
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_ring_handler.setFormatter(_fmt)

logger = logging.getLogger("codesync")
logger.setLevel(logging.DEBUG)


def setup_logging(log_level: str = "INFO") -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=LOG_ROTATE_BYTES, backupCount=LOG_ROTATE_COUNT, encoding="utf-8"
        )
        file_handler.setFormatter(_fmt)
        logger.addHandler(file_handler)
        logger.addHandler(_ring_handler)


def set_qt_bridge(bridge) -> None:
    global _qt_bridge
    _qt_bridge = bridge


def get_ring_handler() -> RingBufferHandler:
    return _ring_handler
