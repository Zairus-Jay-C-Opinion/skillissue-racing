import os
import logging
import hashlib
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from agent.ibt_parser import parse_ibt
from agent.uploader import post_session

log = logging.getLogger(__name__)

MIN_FILE_SIZE = 10 * 1024
SETTLE_WAIT = 3.0  # seconds to wait after file appears before parsing (iRacing writes in bursts)

_seen_hashes: set = set()


def _file_hash(path: str) -> str:
    return hashlib.md5(path.encode()).hexdigest()


class IBTHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".ibt"):
            return
        _process_file(event.src_path)

    def on_moved(self, event):
        # iRacing sometimes writes to a temp name then renames
        if not event.is_directory and event.dest_path.endswith(".ibt"):
            _process_file(event.dest_path)


def _process_file(path: str):
    h = _file_hash(path)
    if h in _seen_hashes:
        return

    # Wait for the write to settle
    time.sleep(SETTLE_WAIT)

    if not os.path.exists(path) or os.path.getsize(path) < MIN_FILE_SIZE:
        log.info(f"Skipping small/missing file: {path}")
        return

    _seen_hashes.add(h)
    log.info(f"New IBT file: {path}")

    data = parse_ibt(path)
    if data is None:
        log.warning(f"Parse returned None for {path}")
        return

    post_session(data)


def start_watcher(folder: str):
    log.info(f"Watching for IBT files in: {folder}")
    Path(folder).mkdir(parents=True, exist_ok=True)

    # Process any existing files on startup (in case files appeared while agent was offline)
    for fname in os.listdir(folder):
        if fname.endswith(".ibt"):
            full = os.path.join(folder, fname)
            h = _file_hash(full)
            _seen_hashes.add(h)  # mark as "already seen" so we don't reprocess old files

    handler = IBTHandler()
    observer = Observer()
    observer.schedule(handler, folder, recursive=False)
    observer.start()
    return observer
