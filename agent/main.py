"""
Agent entry point for Skill Issue Racing.

Starts (on daemon threads):
  - FastAPI backend (uvicorn)
  - IBT file watcher
  - Setup file watcher
  - iRacing SDK live poller

Runs (on main thread via PyQt6):
  - System tray icon + context menu
  - HUD overlay window
  - Agent status mini window
"""

import os
import sys
import logging
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# Filled in once the PyQt6 UI is initialised.
_tray_manager = None


def notify(message: str):
    """Push an event to the status window and optionally show a tray balloon."""
    log.info(f"[notify] {message}")
    try:
        from overlay.widgets import push_event
        push_event(f"— {message}")
    except Exception:
        pass
    if _tray_manager:
        try:
            _tray_manager.notify(message)
        except Exception:
            pass


def _start_backend():
    from backend.main import app as _app
    import uvicorn
    uvicorn.run(
        _app,
        host="127.0.0.1",
        port=int(os.getenv("BACKEND_PORT", "8000")),
        log_level="warning",
    )


def _get_settings_from_db() -> dict:
    try:
        from backend.database import SessionLocal
        from backend.models import Setting
        db = SessionLocal()
        rows = {r.key: r.value for r in db.query(Setting).all()}
        db.close()
        return rows
    except Exception as e:
        log.warning(f"Could not read settings from DB: {e}")
        return {}


def main():
    log.info("Starting Skill Issue Racing Agent...")

    # ── Backend ──
    threading.Thread(target=_start_backend, daemon=True).start()
    time.sleep(2)  # give uvicorn time to bind

    import webbrowser
    webbrowser.open("http://localhost:8000")

    settings = _get_settings_from_db()
    telemetry_folder    = settings.get("telemetry_folder",    os.path.expanduser("~/Documents/iRacing/telemetry"))
    setups_watch_folder = settings.get("setups_watch_folder", os.path.expanduser("~/Downloads/iRacing-setups"))
    iracing_setups_dir  = os.getenv("IRACING_SETUPS_FOLDER",  os.path.expanduser("~/Documents/iRacing/setups"))

    observers = []

    # ── Watchers ──
    from agent.watcher import start_watcher
    observers.append(start_watcher(telemetry_folder))

    from agent.setup_installer import start_setup_watcher
    observers.append(start_setup_watcher(setups_watch_folder, iracing_setups_dir))

    # ── iRacing SDK poller ──
    from agent import iracing_sdk
    iracing_sdk.start()

    # ── PyQt6 UI on main thread ──
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # tray keeps the app alive

    from overlay.widgets import push_event, StatusWindow
    from overlay.main import OverlayWindow, TrayManager

    push_event("Agent started")

    status  = StatusWindow()
    overlay = OverlayWindow(status)

    def _quit():
        for obs in observers:
            try:
                obs.stop()
            except Exception:
                pass
        app.quit()

    global _tray_manager
    _tray_manager = TrayManager(overlay, status, _quit)

    overlay.show()

    log.info("Agent running — Dashboard: http://localhost:8000")
    app.exec()
    os._exit(0)


if __name__ == "__main__":
    main()
