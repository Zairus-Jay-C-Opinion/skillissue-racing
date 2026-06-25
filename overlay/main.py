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
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QCursor

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

        self._locked = False   # start unlocked so the user can drag to position

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.pill  = PillHUD()
        self.strip = SectorStrip()

        layout.addWidget(self.pill,  0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.strip, 0, Qt.AlignmentFlag.AlignHCenter)

        self._context_menu = None   # set by TrayManager after construction

        # ── ACT cue state ────────────────────────────────────────────────────
        self._tips: list = []   # tip titles from last coaching result for this combo
        self._tip_idx = 0

        self._tip_timer = QTimer(self)
        self._tip_timer.timeout.connect(self._next_tip)
        self._tip_timer.start(20_000)   # rotate tip every 20s

        # Real-time coasting trigger
        self._coast_frames = 0
        self._trigger_active = False
        self._trigger_cooldown = False

        self._trigger_clear = QTimer(self)
        self._trigger_clear.setSingleShot(True)
        self._trigger_clear.timeout.connect(self._clear_trigger)

        self._trigger_cooldown_timer = QTimer(self)
        self._trigger_cooldown_timer.setSingleShot(True)
        self._trigger_cooldown_timer.timeout.connect(self._end_cooldown)

        push_event("Tip: Use Borderless Windowed in iRacing for best overlay compatibility")

        self.adjustSize()
        self._position()
        self.pill.set_unlocked_hint(True)   # orange border = drag mode active

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(33)   # ~30 Hz — sufficient for a lap timer display

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
            self.pill.update_lap(None)
            self.pill.update_delta(None)
            self.strip.reset()
            return

        current   = state.get("lap_current_time")
        dist_pct  = state.get("lap_dist_pct", 0.0)
        car       = state.get("car_name", "")
        track     = state.get("track_name", "")

        if car != self._last_car or track != self._last_track:
            self._last_car, self._last_track = car, track
            _load_pb(car, track)
            self._load_coaching(car, track)

        self.pill.update_lap(current)

        pb_at = _interp_pb(dist_pct)
        if pb_at is not None and current is not None:
            self.pill.update_delta(current - pb_at)
        else:
            self.pill.update_delta(None)

        self.strip.set_progress(dist_pct)

        # ── Real-time trigger detection ──────────────────────────────────────
        thr = state.get("throttle") or 0.0
        brk = state.get("brake") or 0.0
        if thr < 0.05 and brk < 0.05:
            self._coast_frames += 1
            if self._coast_frames == 15 and not self._trigger_cooldown:
                self._fire_trigger("coasting")
        else:
            self._coast_frames = 0

    def set_context_menu(self, menu):
        """Called by TrayManager so right-clicking the pill opens the same menu."""
        self._context_menu = menu

    def set_locked(self, locked: bool):
        """
        Locked = click-through (for use during racing).
        Unlocked = draggable with an orange border hint (for positioning).
        """
        self._locked = locked
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, locked)
        self.pill.set_unlocked_hint(not locked)
        self.show()   # window flags only take effect after re-show

    def mousePressEvent(self, e):
        if self._locked:
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif e.button() == Qt.MouseButton.RightButton and self._context_menu:
            self._context_menu.exec(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if not self._locked and e.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag"):
            self.move(e.globalPosition().toPoint() - self._drag)

    # ── ACT cue methods ──────────────────────────────────────────────────────

    def _load_coaching(self, car: str, track: str):
        """Fetch tips for this car+track combo in a background thread."""
        import threading
        threading.Thread(target=self._fetch_coaching_bg, args=(car, track), daemon=True).start()

    def _fetch_coaching_bg(self, car: str, track: str):
        try:
            import httpx
            resp = httpx.get(
                "http://localhost:8000/api/sessions",
                params={"car": car, "track": track, "limit": 1},
                timeout=3,
            )
            if resp.status_code != 200:
                return
            items = resp.json().get("items", [])
            if not items:
                return
            session_id = items[0]["id"]

            resp2 = httpx.get(
                f"http://localhost:8000/api/sessions/{session_id}/coaching",
                timeout=3,
            )
            if resp2.status_code != 200:
                return
            tips = [t["title"] for t in resp2.json().get("tips", []) if t.get("title")]
            QTimer.singleShot(0, lambda: self._set_tips(tips))
        except Exception:
            pass

    def _set_tips(self, tips: list):
        self._tips = tips
        self._tip_idx = 0
        self._update_act_display()

    def _next_tip(self):
        if not self._tips or self._trigger_active:
            return
        self._tip_idx = (self._tip_idx + 1) % len(self._tips)
        self._update_act_display()

    def _fire_trigger(self, text: str):
        self._trigger_active = True
        self._trigger_cooldown = True
        self.pill.update_act(text)
        self._trigger_clear.start(5_000)        # show for 5s then revert to tips
        self._trigger_cooldown_timer.start(10_000)  # no new trigger for 10s

    def _clear_trigger(self):
        self._trigger_active = False
        self._update_act_display()

    def _end_cooldown(self):
        self._trigger_cooldown = False

    def _update_act_display(self):
        if self._trigger_active:
            return
        if self._tips:
            text = self._tips[self._tip_idx]
            self.pill.update_act(text[:16] + "…" if len(text) > 17 else text)
        else:
            self.pill.update_act(None)


# ── TrayManager ─────────────────────────────────────────────────────────────────
class TrayManager:
    """PyQt6 system tray icon with a styled context menu."""

    def __init__(self, overlay: OverlayWindow, status: StatusWindow, quit_fn):
        self._overlay = overlay
        self._status  = status
        self._quit_fn = quit_fn
        self._overlay_locked = False

        # Build menu first so actions are stored as instance vars (prevents GC
        # from breaking the triggered signal connections after __init__ returns)
        self._menu = QMenu()
        self._menu.setStyleSheet("""
            QMenu {
                background-color: #0d0d14;
                border: 1px solid rgba(255,255,255,0.12);
                padding: 6px 0;
                color: #f0f0f0;
                font-family: "Segoe UI";
                font-size: 13px;
                min-width: 220px;
            }
            QMenu::item { padding: 7px 20px 7px 16px; }
            QMenu::item:selected { background-color: rgba(232,93,4,0.15); color: #ffffff; }
            QMenu::item:disabled { color: #555566; }
            QMenu::separator { height: 1px; background: rgba(255,255,255,0.08); margin: 4px 0; }
        """)

        self._header_action = self._menu.addAction("SKILLISSUE RACING")
        self._header_action.setEnabled(False)

        self._menu.addSeparator()

        # Live status lines (updated on menu open via aboutToShow)
        self._agent_status_action = self._menu.addAction("◉  Agent: Running")
        self._agent_status_action.setEnabled(False)
        self._iracing_status_action = self._menu.addAction("○  iRacing: Checking...")
        self._iracing_status_action.setEnabled(False)

        self._last_session_action = self._menu.addAction("")
        self._last_session_action.setEnabled(False)
        self._last_session_action.setVisible(False)

        self._menu.addSeparator()

        self._open_action = self._menu.addAction("Open Dashboard")
        self._open_action.triggered.connect(self._open_dashboard)

        self._overlay_action = self._menu.addAction("Show / Hide Overlay")
        self._overlay_action.triggered.connect(self._toggle_overlay)

        self._lock_action = self._menu.addAction("Lock Overlay  (enable click-through)")
        self._lock_action.triggered.connect(self._toggle_lock)

        self._status_action = self._menu.addAction("Agent Status")
        self._status_action.triggered.connect(self._toggle_status)

        self._menu.addSeparator()

        self._quit_action = self._menu.addAction("Quit")
        self._quit_action.triggered.connect(self._quit)

        # Wire the same menu to the pill's right-click before the tray shows
        overlay.set_context_menu(self._menu)

        # Poll status every 5 s in the background — never blocks the event loop
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._refresh_menu_status)
        self._status_timer.start(5000)
        QTimer.singleShot(500, self._refresh_menu_status)  # initial fetch

        # Defer tray creation until the event loop is running — on Windows 11
        # the system tray isn't guaranteed to be ready during __init__
        self._tray = QSystemTrayIcon(_make_tray_icon())
        self._tray.setToolTip("Skill Issue Racing")
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)
        QTimer.singleShot(500, self._tray.show)

    def _refresh_menu_status(self):
        """Spawn a background thread to fetch status — never blocks the main thread."""
        import threading
        threading.Thread(target=self._fetch_status_bg, daemon=True).start()

    def _fetch_status_bg(self):
        """Runs on a worker thread; posts GUI updates back to the main thread."""
        try:
            import httpx
            resp = httpx.get("http://localhost:8000/api/status", timeout=1.5)
            iracing = resp.json().get("iracing_running", False) if resp.status_code == 200 else False
        except Exception:
            iracing = False

        dot = "◉" if iracing else "○"
        label = "Connected" if iracing else "Not detected"
        iracing_text = f"{dot}  iRacing: {label}"

        last_session_text = None
        try:
            import httpx
            resp = httpx.get("http://localhost:8000/api/sessions?limit=1", timeout=1.5)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items:
                    s = items[0]
                    last_session_text = f"Last: {s.get('track_name','?')}  ·  {s.get('car_name','?')}"
        except Exception:
            pass

        # Dispatch GUI updates back onto the main Qt thread
        QTimer.singleShot(0, lambda: self._apply_status(iracing_text, last_session_text))

    def _apply_status(self, iracing_text, last_session_text):
        self._iracing_status_action.setText(iracing_text)
        if last_session_text:
            self._last_session_action.setText(last_session_text)
            self._last_session_action.setVisible(True)

    def _open_dashboard(self):
        import webbrowser
        webbrowser.open("http://localhost:5173")

    def _toggle_overlay(self):
        if self._overlay.isVisible():
            self._overlay.hide()
        else:
            self._overlay.show()

    def _toggle_lock(self):
        self._overlay_locked = not self._overlay_locked
        self._overlay.set_locked(self._overlay_locked)
        self._lock_action.setText(
            "Unlock Overlay  (drag to reposition)"
            if self._overlay_locked else
            "Lock Overlay  (enable click-through)"
        )

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
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Left single-click — show menu at cursor so the user can unlock
            # the overlay even when click-through is active and the pill
            # can't be right-clicked
            self._menu.popup(QCursor.pos())
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
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

    _tray = TrayManager(overlay, status, _quit)  # must be kept alive
    overlay.show()
    app.exec()


if __name__ == "__main__":
    start_overlay()
