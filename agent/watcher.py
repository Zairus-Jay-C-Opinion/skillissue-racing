import os
import logging
import hashlib
import time
import threading
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from agent.ibt_parser import parse_ibt
from agent.uploader import post_session

log = logging.getLogger(__name__)

MIN_FILE_SIZE = 10 * 1024
SETTLE_WAIT = 5.0       # initial pause after file appears
STABLE_CHECK = 3.0      # seconds between size samples to detect end-of-write
RETRY_INTERVAL = 60     # seconds between retries for locked files

_seen_hashes: set = set()
_pending_lock = threading.Lock()
_pending_files: set = set()  # files still locked by iRacing; retried by _retry_loop


def _file_hash(path: str) -> str:
    return hashlib.md5(path.encode()).hexdigest()


def _is_file_stable(path: str) -> bool:
    """Return True if the file size didn't change over STABLE_CHECK seconds.

    iRacing holds an exclusive write lock for the whole session, so the file
    grows continuously while driving.  Once the size is stable the session is
    over and the lock has been released.
    """
    try:
        s1 = os.path.getsize(path)
        time.sleep(STABLE_CHECK)
        s2 = os.path.getsize(path)
        return s1 == s2 and s2 >= MIN_FILE_SIZE
    except OSError:
        return False


class IBTHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".ibt"):
            threading.Thread(target=_process_file, args=(event.src_path,), daemon=True).start()

    def on_moved(self, event):
        # iRacing sometimes writes to a temp name then renames
        if not event.is_directory and event.dest_path.endswith(".ibt"):
            threading.Thread(target=_process_file, args=(event.dest_path,), daemon=True).start()


def _process_file(path: str):
    h = _file_hash(path)
    if h in _seen_hashes:
        return

    time.sleep(SETTLE_WAIT)

    if not os.path.exists(path) or os.path.getsize(path) < MIN_FILE_SIZE:
        log.info(f"Skipping small/missing file: {path}")
        return

    if not _is_file_stable(path):
        # iRacing is still writing (session in progress) — queue for later
        log.info(f"File still locked by iRacing, will retry after session ends: {path}")
        with _pending_lock:
            _pending_files.add(path)
        return

    _parse_and_upload(path, h)


def _parse_and_upload(path: str, h: str) -> bool:
    data = parse_ibt(path)
    if data is None:
        # Locked or corrupt — keep in pending so the retry loop tries again
        log.warning(f"Parse failed for {path}, will retry")
        with _pending_lock:
            _pending_files.add(path)
        return False

    _seen_hashes.add(h)
    with _pending_lock:
        _pending_files.discard(path)
    post_session(data)
    log.info(f"Session uploaded: {path}")
    return True


def _retry_loop():
    """Periodically retry files that were locked while iRacing was running."""
    while True:
        time.sleep(RETRY_INTERVAL)
        with _pending_lock:
            to_retry = set(_pending_files)

        for path in to_retry:
            h = _file_hash(path)
            if h in _seen_hashes:
                with _pending_lock:
                    _pending_files.discard(path)
                continue
            if not os.path.exists(path) or os.path.getsize(path) < MIN_FILE_SIZE:
                with _pending_lock:
                    _pending_files.discard(path)
                continue
            if not _is_file_stable(path):
                continue  # still being written — check again next cycle
            log.info(f"Retrying previously locked file: {path}")
            _parse_and_upload(path, h)


def start_watcher(folder: str):
    log.info(f"Watching for IBT files in: {folder}")
    Path(folder).mkdir(parents=True, exist_ok=True)

    # Mark files already on disk as seen so we don't reprocess old sessions
    for fname in os.listdir(folder):
        if fname.endswith(".ibt"):
            full = os.path.join(folder, fname)
            _seen_hashes.add(_file_hash(full))

    handler = IBTHandler()
    observer = Observer()
    observer.schedule(handler, folder, recursive=False)
    observer.start()

    threading.Thread(target=_retry_loop, daemon=True).start()

    return observer
