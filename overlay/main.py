"""
PyQt6 transparent HUD overlay for iRacing.

Key Qt flags used:
- WindowStaysOnTopHint: always renders above iRacing
- FramelessWindowHint: no title bar / window chrome
- Tool: keeps it out of the taskbar
- WA_TranslucentBackground: glass-clear window behind text
- WindowTransparentForInput: mouse clicks pass through to iRacing
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMouseEvent

from overlay.widgets import DeltaWidget, LapTimeWidget, BrakeCueWidget

log = logging.getLogger(__name__)

_pb_trace: dict | None = None  # {dist_pct: lap_time} — loaded from DB at startup


def _load_pb(car: str, track: str):
    """Pull best-lap telemetry trace from DB for delta calculation."""
    global _pb_trace
    try:
        import httpx, json
        resp = httpx.get(f"http://localhost:8000/api/pbs/{car}/{track}", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            trace = data.get("lap_telemetry")
            if trace:
                raw = json.loads(trace) if isinstance(trace, str) else trace
                _pb_trace = {frame["dist_pct"]: frame["t"] for frame in raw if frame.get("dist_pct") is not None}
    except Exception as e:
        log.debug(f"Could not load PB trace: {e}")


def _interpolate_pb_time(dist_pct: float) -> float | None:
    if not _pb_trace:
        return None
    keys = sorted(_pb_trace.keys())
    if not keys:
        return None
    # Linear interpolation between nearest keyframes
    lo = max((k for k in keys if k <= dist_pct), default=None)
    hi = min((k for k in keys if k >= dist_pct), default=None)
    if lo is None or hi is None:
        return None
    if lo == hi:
        return _pb_trace[lo]
    t = (dist_pct - lo) / (hi - lo)
    return _pb_trace[lo] + t * (_pb_trace[hi] - _pb_trace[lo])


class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.lap_widget = LapTimeWidget()
        self.delta_widget = DeltaWidget()
        self.brake_widget = BrakeCueWidget()

        layout.addWidget(self.lap_widget)
        layout.addWidget(self.delta_widget)
        layout.addWidget(self.brake_widget)

        self.adjustSize()
        self._load_position()

        self._lap_start_time: float | None = None
        self._prev_dist: float | None = None
        self._last_car = None
        self._last_track = None

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(16)  # ~60Hz

    def _load_position(self):
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
        self.move(800, 40)

    def _tick(self):
        from agent import iracing_sdk
        state = iracing_sdk.get_state()
        if not state:
            # Show placeholder values so the overlay is visible for positioning
            self.setVisible(True)
            self.lap_widget.update(None, None)
            self.delta_widget.update_delta(None)
            return

        self.setVisible(True)

        current_time = state.get("lap_current_time")
        best_time = state.get("lap_best_time")
        dist_pct = state.get("lap_dist_pct", 0)

        self.lap_widget.update(current_time, best_time)

        # Delta vs PB
        pb_time_at_pos = _interpolate_pb_time(dist_pct)
        if pb_time_at_pos is not None and current_time is not None:
            delta = current_time - pb_time_at_pos
            self.delta_widget.update_delta(delta)
        else:
            self.delta_widget.update_delta(None)

        self._prev_dist = dist_pct

    # Allow dragging by holding Alt + drag (input passthrough is on by default)
    def mousePressEvent(self, event: QMouseEvent):
        if event.modifiers() == Qt.KeyboardModifier.AltModifier:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.modifiers() == Qt.KeyboardModifier.AltModifier and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)


def start_overlay():
    app = QApplication.instance() or QApplication(sys.argv)
    window = OverlayWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    start_overlay()
