"""
Option B overlay ACT test — fakes iRacing state so the full tick/trigger
pipeline runs without iRacing being open.

Run from repo root:
    python -m scripts.test_overlay_act

What to watch:
  t=0s   Overlay + Status Window appear. Status Window shows borderless tip.
  t=2s   3 dummy tips injected → ACT pill shows first tip title.
  t=5s   Throttle + brake forced to 0 → coasting counter starts.
  t=5.5s ACT flips to "coasting" (orange text, held 5s).
  t=10s  Cue clears → ACT returns to tip cycling.
  t=22s  Second tip appears (20s rotation), then third at t=42s.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── 1. Inject fake iRacing state before overlay imports the module ──────────
from agent import iracing_sdk

iracing_sdk._state.update({
    "car_name":         "Ferrari 296 GT3",
    "track_name":       "Spa-Francorchamps",
    "throttle":         0.85,
    "brake":            0.0,
    "lap_current_time": 47.123,
    "lap_dist_pct":     0.34,
    "speed_kph":        195.0,
    "rpm":              7200,
    "gear":             5,
    "lap_num":          3,
    "lap_best_time":    139.2,
    "lap_last_time":    140.5,
    "fl_temp": 88.0, "fr_temp": 87.5,
    "rl_temp": 85.0, "rr_temp": 84.5,
})

# ── 2. Launch overlay ────────────────────────────────────────────────────────
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from overlay.widgets import StatusWindow, push_event
from overlay.main import OverlayWindow, TrayManager

app = QApplication.instance() or QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

status  = StatusWindow()
overlay = OverlayWindow(status)

tray = TrayManager(overlay, status, app.quit)
overlay.show()
status.show()

# ── 3. Scheduled state changes ───────────────────────────────────────────────

def phase_inject_tips():
    """t=2s — directly inject test tips to verify cycling works even if no
    coaching exists in the DB for this combo."""
    overlay._set_tips(["Brake later T1", "Trail brake S2", "Smooth apex"])
    push_event("TEST [2s] Injected 3 tips — ACT should show 'Brake later T1'")

def phase_start_coasting():
    """t=5s — zero both inputs to start the coasting counter (15 frames = 0.5s)."""
    iracing_sdk._state.update({"throttle": 0.0, "brake": 0.0})
    push_event("TEST [5s] Throttle + brake set to 0 — trigger fires in ~0.5s")

def phase_restore_throttle():
    """t=12s — restore throttle so the trigger clears and tips resume."""
    iracing_sdk._state.update({"throttle": 0.9, "brake": 0.0})
    push_event("TEST [12s] Throttle restored — ACT should revert to tips")

def phase_done():
    push_event("TEST [30s] Done. Close window or Quit from tray.")

QTimer.singleShot( 2_000, phase_inject_tips)
QTimer.singleShot( 5_000, phase_start_coasting)
QTimer.singleShot(12_000, phase_restore_throttle)
QTimer.singleShot(30_000, phase_done)

app.exec()
