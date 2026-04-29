from __future__ import annotations
from pathlib import Path
from typing import Callable

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from codesync.utils.logger import logger


class _ChangeHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self._callback = callback

    def on_any_event(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._callback(str(event.src_path))


class FileWatcher:
    """Watches a local directory and fires a callback on any file change."""

    def __init__(self):
        self._observers: dict[str, Observer] = {}  # profile_id -> Observer

    def start_watch(self, profile_id: str, local_path: str, callback: Callable[[str], None]) -> None:
        self.stop_watch(profile_id)
        path = str(Path(local_path).expanduser())
        handler = _ChangeHandler(callback)
        observer = Observer()
        observer.schedule(handler, path, recursive=True)
        observer.daemon = True
        observer.start()
        self._observers[profile_id] = observer
        logger.info("Watching local directory %s for profile %s", path, profile_id)

    def stop_watch(self, profile_id: str) -> None:
        obs = self._observers.pop(profile_id, None)
        if obs is not None:
            obs.stop()
            obs.join(timeout=3)
            logger.info("Stopped file watcher for profile %s", profile_id)

    def stop_all(self) -> None:
        for profile_id in list(self._observers):
            self.stop_watch(profile_id)
