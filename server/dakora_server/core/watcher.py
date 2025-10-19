from __future__ import annotations
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from typing import Callable

class _Handler(FileSystemEventHandler):
    def __init__(self, on_change: Callable[[], None]) -> None:
        super().__init__()
        self.on_change = on_change
    def on_any_event(self, event):  # create/modify/move/delete
        self.on_change()

class Watcher:
    def __init__(self, path: str | Path, on_change: Callable[[], None]) -> None:
        self.path = str(Path(path))
        self._observer = Observer()
        self._handler = _Handler(on_change)

    def start(self):
        self._observer.schedule(self._handler, self.path, recursive=True)
        self._observer.start()

    def stop(self):
        self._observer.stop()
        self._observer.join()