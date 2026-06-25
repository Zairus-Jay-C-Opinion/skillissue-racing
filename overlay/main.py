"""
Overlay entry point for Skill Issue Racing.

Exposes:
  OverlayWindow  — frameless HUD pill + sector strip (stays on top, click-through)
  TrayManager    — PyQt6 system tray icon with context menu
  start_overlay() — standalone launcher for testing without the full agent
"""

import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction

from overlay.widgets import PillHUD, SectorStrip, StatusWindow, push_event

log = logging.getLogger(__name__)

_pb_trace: dict | None = None


def _load_pb(car: str, track: str):
    global _pb_trace
    try:
        import httpx, json
        resp = httpx.get(f"http://localhost:8000/api/pbs/{car}/{track}", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            trace = data.get("lap_telemetry")
            if trace:
                raw = json.loads(trace) if isinstance(trace, str) else trace
                _pb_trace = {f["dist_pct"]: f["t"] for f in raw if f.get("dist_pct") is not None}
    except Exception as e:
        log.debug(f"Could not load PB trace: {e}")


def _interp_pb(dist_pct: float) -> float | None:
    if not _pb_trace:
        return None
    keys = sorted(_pb_trace.keys())
    lo = max((k for k in keys if k <= dist_pct), default=None)
    hi = min((k for k in keys if k >= dist_pct), default=None)
    if lo is None or hi is None:
        return None
    if lo == hi:
        return _pb_trace[lo]
    t = (dist_pct - lo) / (hi - lo)
    return _pb_trace[lo] + t * (_pb_trace[hi] - _pb_trace[lo])


def _make_tray_icon() -> QIcon:
    """Orange circle icon for the system tray."""
    pm = QPixmap(32, 32)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(232, 93, 4))   # brand orange
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 4, 24, 24)
    p.end()
    return QIcon(pm)


# ── OverlayWindow ───────────────────────────────────────────────────────────────
class OverlayWindow(QWidget):
    """Frameless, transparent, click-through HUD with pill + sector strip."""

    def __init__(self, status_window: StatusWindow):
        super().__init__()
        self._status = status_window
        self._last_car = ""
        self._last_track = ""

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.pill  = PillHUD()
        self.strip = SectorStrip()

        layout.addWidget(self.pill,  0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.strip, 0, Qt.AlignmentFlag.AlignHCenter)

        self.adjustSize()
        self._position()

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(16)   # ~60 Hz

    def _position(self):
        """Read saved position from backend settings, or default to top-center."""
        try:
            import httpx
            resp = httpx.get("http://localhost:8000/api/settings", timeout=2)
            if resp.status_code == 200:
                s = resp.json()
                x = int(s.get("overlay_position_x", 960))
                y = int(s.get("overlay_position_y", 40))
                self.move(x - self.width() // 2, y)
                return
        except Exception:
            pass
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, 40)

    def _tick(self):
        from agent import iracing_sdk
        state = iracing_sdk.get_state()

        if not state:
            self.setVisible(True)
            self.pill.update_lap(None)
            self.pill.update_delta(None)
            self.strip.reset()
            return

        self.setVisible(True)

        current   = state.get("lap_current_time")
        dist_pct  = state.get("lap_dist_pct", 0.0)
        car       = state.get("car_name", "")
        track     = state.get("track_name", "")

        if car != self._last_car or track != self._last_track:
            self._last_car, self._last_track = car, track
            _load_pb(car, track)

        self.pill.update_lap(current)

        pb_at = _interp_pb(dist_pct)
        if pb_at is not None and current is not None:
            self.pill.update_delta(current - pb_at)
        else:
            self.pill.update_delta(None)

        self.strip.set_progress(dist_pct)

    # Alt + drag to reposition
    def mousePressEvent(self, e):
        if e.modifiers() == Qt.KeyboardModifier.AltModifier:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.modifiers() == Qt.KeyboardModifier.AltModifier and hasattr(self, "_drag"):
            self.move(e.globalPosition().toPoint() - self._drag)


# ── TrayManager ─────────────────────────────────────────────────────────────────
class TrayManager:
    """PyQt6 system tray icon with a styled context menu."""

    def __init__(self, overlay: OverlayWindow, status: StatusWindow, quit_fn):
        self._overlay = overlay
        self._status  = status
        self._quit_fn = quit_fn

        self._tray = QSystemTrayIcon(_make_tray_icon())
        self._tray.setToolTip("Skill Issue Racing")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a0f18;
                border: 1px solid rgba(255,255,255,0.12);
                padding: 4px 0;
                color: #f0f0f0;
                font-family: "Segoe UI";
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px 6px 14px;
            }
            QMenu::item:selected {
                background-color: rgba(80,50,50,0.8);
                color: #ffffff;
            }
            QMenu::item:disabled {
                color: #888899;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255,255,255,0.10);
                margin: 3px 0;
            }
        """)

        header = menu.addAction("Skill Issue Racing v1.0")
        header.setEnabled(False)
        menu.addSeparator()

        open_action = menu.addAction("Open Dashboard")
        open_action.triggered.connect(self._open_dashboard)

        overlay_action = menu.addAction("Show / Hide Overlay")
        overlay_action.triggered.connect(self._toggle_overlay)

        status_action = menu.addAction("Agent Status")
        status_action.triggered.connect(self._toggle_status)

        menu.addSeparator()

        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _open_dashboard(self):
        import webbrowser
        webbrowser.open("http://localhost:5173")

    def _toggle_overlay(self):
        if self._overlay.isVisible():
            self._overlay.hide()
        else:
            self._overlay.show()

    def _toggle_status(self):
        if self._status.isVisible():
            self._status.hide()
        else:
            screen = QApplication.primaryScreen().geometry()
            self._status.move(
                screen.width()  - self._status.width()  - 24,
                screen.height() - self._status.height() - 64,
            )
            self._status.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open_dashboard()

    def _quit(self):
        self._quit_fn()

    def notify(self, message: str):
        self._tray.showMessage(
            "Skill Issue Racing", message,
            QSystemTrayIcon.MessageIcon.Information, 3000,
        )


# ── Standalone launcher ─────────────────────────────────────────────────────────
def start_overlay():
    """
    Create the full UI stack without the agent backend.
    Use this for testing the overlay visually without iRacing.
    """
    push_event("Overlay started (standalone mode)")

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    status  = StatusWindow()
    overlay = OverlayWindow(status)

    def _quit():
        app.quit()

    TrayManager(overlay, status, _quit)
    overlay.show()
    app.exec()


if __name__ == "__main__":
    start_overlay()
