"""
Auto setup installer — watches a folder for .sto files and copies them
to the correct iRacing setups subfolder by reading the CarPath XML tag.
"""

import os
import shutil
import logging
import time
from pathlib import Path
from xml.etree import ElementTree

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

log = logging.getLogger(__name__)

SETTLE_WAIT = 1.5


def _extract_car_path(sto_path: str) -> str | None:
    try:
        tree = ElementTree.parse(sto_path)
        root = tree.getroot()
        # The CarPath element can be a direct child or nested
        for elem in root.iter("CarPath"):
            return elem.text.strip() if elem.text else None
    except Exception as e:
        log.error(f"Failed to parse .sto XML {sto_path}: {e}")
    return None


class SetupHandler(FileSystemEventHandler):
    def __init__(self, iracing_setups_root: str):
        self.iracing_setups_root = iracing_setups_root

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".sto"):
            _install(event.src_path, self.iracing_setups_root)

    def on_moved(self, event):
        if not event.is_directory and event.dest_path.endswith(".sto"):
            _install(event.dest_path, self.iracing_setups_root)


def _install(sto_path: str, iracing_setups_root: str):
    time.sleep(SETTLE_WAIT)
    if not os.path.exists(sto_path):
        return

    car_path = _extract_car_path(sto_path)
    if not car_path:
        _move_to_unknown(sto_path)
        log.warning(f"Could not determine car for {sto_path}, moved to unknown/")
        return

    dest_dir = os.path.join(iracing_setups_root, car_path)
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        log.info(f"Created setup folder: {dest_dir}")

    filename = os.path.basename(sto_path)
    dest = os.path.join(dest_dir, filename)

    # Avoid overwrite — append timestamp suffix
    if os.path.exists(dest):
        base, ext = os.path.splitext(filename)
        dest = os.path.join(dest_dir, f"{base}_{int(time.time())}{ext}")

    shutil.copy2(sto_path, dest)
    log.info(f"Setup installed: {filename} → {dest}")

    # Notify via system tray if available
    try:
        from agent.main import notify
        notify(f"Setup installed: {filename} → {car_path}")
    except Exception:
        pass


def _move_to_unknown(sto_path: str):
    unknown_dir = os.path.join(os.path.dirname(sto_path), "unknown")
    os.makedirs(unknown_dir, exist_ok=True)
    shutil.move(sto_path, os.path.join(unknown_dir, os.path.basename(sto_path)))


def start_setup_watcher(watch_folder: str, iracing_setups_root: str):
    Path(watch_folder).mkdir(parents=True, exist_ok=True)
    handler = SetupHandler(iracing_setups_root)
    observer = Observer()
    observer.schedule(handler, watch_folder, recursive=False)
    observer.start()
    log.info(f"Watching for setups in: {watch_folder}")
    return observer
