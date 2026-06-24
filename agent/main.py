"""
Agent entry point.
Starts:
  - The FastAPI backend (in a background thread)
  - The IBT file watcher
  - The iRacing SDK live poller
  - The setup file watcher
  - The system tray icon
  - The PyQt6 overlay (if available)
"""

import os
import sys
import logging
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)

_tray_icon = None


def notify(message: str):
    if _tray_icon:
        try:
            _tray_icon.showMessage("Sim Companion", message)
        except Exception:
            pass
    log.info(f"[notify] {message}")


def _start_backend():
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=int(os.getenv("BACKEND_PORT", "8000")),
        log_level="warning",
    )


def _get_settings_from_db() -> dict:
    """Read folder paths from DB (set during onboarding)."""
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


def _start_tray(observers):
    """System tray icon using pystray."""
    global _tray_icon
    try:
        from PIL import Image, ImageDraw
        import pystray

        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill=(30, 180, 80))  # green circle

        def on_quit(icon, item):
            log.info("Quit requested from tray")
            for obs in observers:
                try:
                    obs.stop()
                except Exception:
                    pass
            icon.stop()
            os._exit(0)

        menu = pystray.Menu(
            pystray.MenuItem("Sim Companion Running", None, enabled=False),
            pystray.MenuItem("Open Dashboard", lambda *_: _open_browser()),
            pystray.MenuItem("Quit", on_quit),
        )

        _tray_icon = pystray.Icon("SimCompanion", img, "Sim Companion", menu)
        _tray_icon.run()
    except ImportError:
        log.warning("pystray/Pillow not installed — no system tray icon")
        # Keep main thread alive
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            pass


def _open_browser():
    import webbrowser
    webbrowser.open("http://localhost:8000")


def main():
    log.info("Starting Sim Racing Companion Agent...")

    # Backend in background thread
    backend_thread = threading.Thread(target=_start_backend, daemon=True)
    backend_thread.start()
    time.sleep(2)  # let backend initialize and seed settings

    settings = _get_settings_from_db()
    telemetry_folder = settings.get("telemetry_folder", os.path.expanduser("~/Documents/iRacing/telemetry"))
    setups_watch_folder = settings.get("setups_watch_folder", os.path.expanduser("~/Downloads/iRacing-setups"))
    iracing_setups_folder = os.getenv("IRACING_SETUPS_FOLDER", os.path.expanduser("~/Documents/iRacing/setups"))

    observers = []

    # IBT watcher
    from agent.watcher import start_watcher
    ibt_obs = start_watcher(telemetry_folder)
    observers.append(ibt_obs)

    # Setup installer watcher
    from agent.setup_installer import start_setup_watcher
    setup_obs = start_setup_watcher(setups_watch_folder, iracing_setups_folder)
    observers.append(setup_obs)

    # iRacing SDK poller
    from agent import iracing_sdk
    iracing_sdk.start()

    # Overlay (optional — only if PyQt6 installed)
    try:
        from overlay.main import start_overlay
        overlay_thread = threading.Thread(target=start_overlay, daemon=True)
        overlay_thread.start()
    except ImportError:
        log.info("PyQt6 not found — overlay disabled")

    log.info("Agent running. Dashboard: http://localhost:8000")
    _start_tray(observers)


if __name__ == "__main__":
    main()
