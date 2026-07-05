"""
Live iRacing shared memory reader.
Polls at ~60Hz and exposes current telemetry values to the overlay.
Gracefully disables itself if iRacing is not running or the SDK can't connect.
"""

import threading
import logging
import time

log = logging.getLogger(__name__)

_state: dict = {}
_lock = threading.Lock()
_running = False


def get_state() -> dict:
    with _lock:
        return dict(_state)


def _poll_loop():
    global _running
    try:
        import irsdk
        ir = irsdk.IRSDK()
        connected = False

        while _running:
            if not connected:
                if ir.startup():
                    connected = True
                    log.info("iRacing SDK connected")
                    # Car and track come from session_info YAML, not telemetry vars.
                    # ir['WeekendInfo'] routes through IRSDK's own YAML parser
                    # (__getitem__ falls back to _get_session_info for non-telemetry
                    # keys) — parse_to() writes to a file and returns None, it isn't
                    # a getter.
                    try:
                        weekend = ir['WeekendInfo'] or {}
                    except Exception:
                        weekend = {}
                    _car_name = weekend.get("CarName", "Unknown Car")
                    _track_name = weekend.get(
                        "TrackDisplayName",
                        weekend.get("TrackName", "Unknown Track"),
                    )
                    with _lock:
                        _state["car_name"]   = _car_name
                        _state["track_name"] = _track_name
                else:
                    time.sleep(2)
                    continue

            if not ir.is_connected:
                connected = False
                with _lock:
                    _state.clear()
                log.info("iRacing disconnected, waiting...")
                time.sleep(2)
                continue

            ir.freeze_var_buffer_latest()
            with _lock:
                _state.update({
                    "speed_kph":        round((ir["Speed"] or 0) * 3.6, 1),
                    "rpm":              ir["RPM"],
                    "gear":             ir["Gear"],
                    "throttle":         ir["Throttle"],
                    "brake":            ir["Brake"],
                    "lap_dist_pct":     ir["LapDistPct"],
                    "lap_current_time": ir["LapCurrentLapTime"],
                    "lap_best_time":    ir["LapBestLapTime"],
                    "lap_last_time":    ir["LapLastLapTime"],
                    "session_time":     ir["SessionTime"],
                    "lap_num":          ir["Lap"],
                    "fl_temp":          ir["LFtempCM"],
                    "fr_temp":          ir["RFtempCM"],
                    "rl_temp":          ir["LRtempCM"],
                    "rr_temp":          ir["RRtempCM"],
                })

            time.sleep(1 / 60)

    except ImportError:
        log.warning("irsdk not installed — live overlay disabled")
    except Exception as e:
        log.error(f"iRacing SDK poll error: {e}")
    finally:
        _running = False


def start():
    global _running
    _running = True
    t = threading.Thread(target=_poll_loop, daemon=True)
    t.start()
    return t


def stop():
    global _running
    _running = False
