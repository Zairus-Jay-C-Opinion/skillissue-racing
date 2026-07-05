"""
IBT binary file parser for iRacing telemetry.

IBT files contain:
 - A disk sub header (version, session info offset/len, var header offset, etc.)
 - A YAML-ish session info string
 - A list of variable headers (name, type, offset, count, description, unit)
 - N-frame data blocks (one frame per sample, typically 60Hz)

We use pyirsdk's ibt reader which abstracts all of this.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

try:
    import irsdk
    IRSDK_AVAILABLE = True
except ImportError:
    irsdk = None
    IRSDK_AVAILABLE = False

log = logging.getLogger(__name__)

# Channels we care about — grouped for clarity
TYRE_TEMP_CHANNELS = [
    "LFtempCL", "LFtempCM", "LFtempCR",
    "RFtempCL", "RFtempCM", "RFtempCR",
    "LRtempCL", "LRtempCM", "LRtempCR",
    "RRtempCL", "RRtempCM", "RRtempCR",
]
TYRE_WEAR_CHANNELS = ["LFwearL", "LFwearM", "LFwearR", "RFwearL", "RFwearM", "RFwearR",
                      "LRwearL", "LRwearM", "LRwearR", "RRwearL", "RRwearM", "RRwearR"]
SUSPENSION_CHANNELS = [
    "LFshockDefl", "RFshockDefl", "LRshockDefl", "RRshockDefl",
    "LFspringDefl", "RFspringDefl",
    "RideHeight",
]
DRIVING_CHANNELS = ["Throttle", "Brake", "Clutch", "Speed", "RPM", "Gear"]
LAP_CHANNELS = [
    "LapDistPct", "LapCurrentLapTime", "LapLastLapTime", "LapBestLapTime",
    "SessionTime", "SessionNum", "Lap",
]
POSITION_CHANNELS = ["Lat", "Lon"]
CONDITION_CHANNELS = ["WeatherType", "AirTemp", "TrackTemp", "TrackTempCrew"]

ALL_CHANNELS = (
    TYRE_TEMP_CHANNELS + TYRE_WEAR_CHANNELS + SUSPENSION_CHANNELS
    + DRIVING_CHANNELS + LAP_CHANNELS + POSITION_CHANNELS + CONDITION_CHANNELS
)

MIN_FILE_SIZE = 10 * 1024  # 10 KB


def _avg(a, b, c):
    vals = [v for v in (a, b, c) if v is not None]
    return sum(vals) / len(vals) if vals else None


def _coasting_events(throttle_trace: list, brake_trace: list) -> int:
    """Count distinct stretches where both throttle and brake are ~0 for >0.3s at 60Hz = 18 frames."""
    count = 0
    run = 0
    threshold = 18  # ~0.3s at 60 Hz
    for t, b in zip(throttle_trace, brake_trace):
        if (t or 0) < 0.05 and (b or 0) < 0.05:
            run += 1
        else:
            if run >= threshold:
                count += 1
            run = 0
    return count


def _oversteer_events(lateral_g_trace: list, steering_trace: list) -> int:
    """
    Detect lateral G spikes without corresponding steering changes.
    Simple heuristic: |lateral_G| > 2.5 with |steering_change| < 5° in same window.
    """
    count = 0
    in_event = False
    for i, g in enumerate(lateral_g_trace):
        if g is None:
            continue
        if abs(g) > 2.5:
            steer_delta = abs((steering_trace[i] or 0) - (steering_trace[i - 1] or 0)) if i > 0 else 0
            if steer_delta < 5:
                if not in_event:
                    count += 1
                    in_event = True
            else:
                in_event = False
        else:
            in_event = False
    return count


def parse_ibt(filepath: str) -> Optional[dict]:
    """
    Parse an iRacing .ibt file. Returns a structured session dict or None on failure.
    """
    if not IRSDK_AVAILABLE:
        log.error("pyirsdk not installed — cannot parse real IBT files. Run: pip install pyirsdk")
        return None

    if os.path.getsize(filepath) < MIN_FILE_SIZE:
        log.warning(f"Skipping small file: {filepath}")
        return None

    try:
        ir = irsdk.IBT()
        ir.open(filepath)
    except Exception as e:
        log.error(f"Failed to open IBT file {filepath}: {e}")
        return None

    try:
        return _extract(ir, filepath)
    except Exception as e:
        log.error(f"Failed to parse IBT file {filepath}: {e}")
        return None
    finally:
        try:
            ir.close()
        except Exception:
            pass


def _sector_bests(lap_nums, dist_pct_arr, lap_current_arr, lap_total_time: dict):
    """
    Detect S1/S2/S3 times per lap using 1/3 and 2/3 lap-distance thresholds.
    Returns (s1_best, s2_best, s3_best) — all None if data is insufficient.
    """
    from collections import defaultdict

    S1_THRESH = 1 / 3
    S2_THRESH = 2 / 3

    by_lap = defaultdict(list)
    for i, ln in enumerate(lap_nums):
        if ln is not None:
            by_lap[int(ln)].append(i)

    s1_times, s2_times, s3_times = [], [], []

    for lap_num, indices in sorted(by_lap.items()):
        total = lap_total_time.get(lap_num)
        if not total:
            continue

        # Skip incomplete laps — if first frame is already well past start line
        first_dp = dist_pct_arr[indices[0]] if indices and indices[0] < len(dist_pct_arr) else None
        if first_dp is not None and first_dp > 0.10:
            continue

        s1_cross = s2_cross = None
        for idx in indices:
            dp = dist_pct_arr[idx] if idx < len(dist_pct_arr) else None
            ct = lap_current_arr[idx] if idx < len(lap_current_arr) else None
            if dp is None or ct is None:
                continue
            if s1_cross is None and dp >= S1_THRESH:
                s1_cross = ct
            if s2_cross is None and dp >= S2_THRESH:
                s2_cross = ct
                break  # have both, no need to continue

        if s1_cross and s2_cross and s1_cross < s2_cross < total:
            s1_times.append(s1_cross)
            s2_times.append(s2_cross - s1_cross)
            s3_times.append(total - s2_cross)

    if not s1_times:
        return None, None, None

    return round(min(s1_times), 4), round(min(s2_times), 4), round(min(s3_times), 4)


def _extract(ir: "irsdk.IBT", filepath: str) -> dict:
    session_info = ir.session_info

    # Pull session/weekend metadata from the YAML block
    weekend = session_info.get("WeekendInfo", {})
    driver_info = session_info.get("DriverInfo", {})
    car_name = weekend.get("CarName", "Unknown Car")
    track_name = weekend.get("TrackDisplayName", weekend.get("TrackName", "Unknown Track"))
    # WeekendOptions.Date is the in-sim date configured for the session setup —
    # for solo practice/test sessions this is often reused unchanged across many
    # real-world sessions, so it can't be trusted as "when this was driven."
    # The file's mtime (set once iRacing releases its write lock) is the actual
    # real-world timestamp.
    try:
        session_date = datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
    except Exception:
        session_date = datetime.utcnow().isoformat()

    # Collect per-frame data
    frames = {ch: [] for ch in ALL_CHANNELS}
    total_frames = ir.var_headers_dict.get("SessionTime", {}).get("count", 0)

    # irsdk IBT: iterate using ir[channel] which returns the full array
    available = set(ir.var_headers_dict.keys())
    for ch in ALL_CHANNELS:
        if ch in available:
            frames[ch] = list(ir[ch]) if ir[ch] is not None else []

    total_frames = max(len(v) for v in frames.values() if v)

    # ── Lap segmentation ────────────────────────────────────────────────────
    lap_nums = frames.get("Lap", [])
    lap_times = frames.get("LapLastLapTime", [])
    best_lap_time = None
    avg_lap_time = None
    lap_count = 0

    # Collect valid completed lap times (LapLastLapTime updates when a lap completes)
    completed_laps = []
    lap_total_time = {}   # lap_num → completed lap time (for sector detection)
    prev_lap = None
    for i, lap in enumerate(lap_nums):
        if lap is None:
            continue
        if prev_lap is not None and lap != prev_lap:
            t = lap_times[i] if i < len(lap_times) else None
            if t and 20 < t < 600:  # ignore outlap/in-lap extremes
                completed_laps.append(t)
                lap_total_time[prev_lap] = t
        prev_lap = lap

    if completed_laps:
        best_lap_time = round(min(completed_laps), 4)
        avg_lap_time = round(sum(completed_laps) / len(completed_laps), 4)
        lap_count = len(completed_laps)

    # ── PB lap telemetry trace (for overlay VS PB delta) ──────────────────
    pb_telemetry = None
    if best_lap_time is not None and lap_total_time:
        best_lap_num = min(lap_total_time, key=lap_total_time.get)
        lap_current_arr = frames.get("LapCurrentLapTime", [])
        dist_arr = frames.get("LapDistPct", [])
        pb_frames = []
        for i, ln in enumerate(lap_nums):
            if ln != best_lap_num:
                continue
            if i >= len(lap_current_arr) or i >= len(dist_arr):
                continue
            t_val = lap_current_arr[i]
            d_val = dist_arr[i]
            if t_val is not None and d_val is not None:
                pb_frames.append({
                    "dist_pct": round(float(d_val), 4),
                    "t": round(float(t_val), 4),
                })
        if pb_frames:
            pb_telemetry = json.dumps(pb_frames[::5])  # ~12Hz sample from 60Hz

    # ── Sector detection ────────────────────────────────────────────────────
    sector_1_best, sector_2_best, sector_3_best = _sector_bests(
        lap_nums,
        frames.get("LapDistPct", []),
        frames.get("LapCurrentLapTime", []),
        lap_total_time,
    )

    # ── Tyre data per lap ──────────────────────────────────────────────────
    tyre_laps = []
    if lap_nums:
        laps_seen = sorted(set(l for l in lap_nums if l is not None))
        for lap_num in laps_seen:
            indices = [i for i, l in enumerate(lap_nums) if l == lap_num]
            if not indices:
                continue

            def avg_channel(base_channels):
                vals = []
                for ch in base_channels:
                    ch_data = frames.get(ch, [])
                    lap_vals = [ch_data[i] for i in indices if i < len(ch_data) and ch_data[i] is not None]
                    if lap_vals:
                        vals.append(sum(lap_vals) / len(lap_vals))
                return round(sum(vals) / len(vals), 2) if vals else None

            fl_avg = avg_channel(["LFtempCL", "LFtempCM", "LFtempCR"])
            fr_avg = avg_channel(["RFtempCL", "RFtempCM", "RFtempCR"])
            rl_avg = avg_channel(["LRtempCL", "LRtempCM", "LRtempCR"])
            rr_avg = avg_channel(["RRtempCL", "RRtempCM", "RRtempCR"])

            def last_wear(ch):
                data = frames.get(ch, [])
                lap_vals = [data[i] for i in indices if i < len(data) and data[i] is not None]
                return round(lap_vals[-1], 4) if lap_vals else None

            fl_wear = last_wear("LFwearM")
            fr_wear = last_wear("RFwearM")
            rl_wear = last_wear("LRwearM")
            rr_wear = last_wear("RRwearM")

            tyre_laps.append({
                "lap_number": lap_num,
                "fl_avg_temp": fl_avg,
                "fr_avg_temp": fr_avg,
                "rl_avg_temp": rl_avg,
                "rr_avg_temp": rr_avg,
                "fl_wear": fl_wear,
                "fr_wear": fr_wear,
                "rl_wear": rl_wear,
                "rr_wear": rr_wear,
            })

    # ── Driving input summary ──────────────────────────────────────────────
    throttle = frames.get("Throttle", [])
    brake = frames.get("Brake", [])
    coasting_zones = _coasting_events(throttle, brake)

    # Oversteer requires lateral G — iRacing doesn't expose it directly; use a proxy
    # (we skip for now; the field will be 0 until a better sensor is found)
    oversteer_count = 0

    avg_max_brake = None
    if brake:
        valid_brake = [b for b in brake if b is not None]
        avg_max_brake = round(max(valid_brake) * 100, 1) if valid_brake else None

    # Throttle application point: average LapDistPct at which throttle > 0.9
    throttle_points = []
    dist = frames.get("LapDistPct", [])
    for i, t in enumerate(throttle):
        if t and t > 0.9 and i < len(dist) and dist[i] is not None:
            throttle_points.append(dist[i] * 100)
    avg_throttle_point = round(sum(throttle_points) / len(throttle_points), 1) if throttle_points else None

    # ── Conditions ─────────────────────────────────────────────────────────
    def first_valid(ch):
        data = frames.get(ch, [])
        for v in data:
            if v is not None:
                return v
        return None

    air_temp = first_valid("AirTemp")
    track_temp = first_valid("TrackTemp") or first_valid("TrackTempCrew")
    weather_type = first_valid("WeatherType")
    weather = "Wet" if weather_type == 1 else "Dry"

    # ── Compact raw_json (subsample to 1Hz to keep DB size sane) ──────────
    speed = frames.get("Speed", [])
    rpm = frames.get("RPM", [])
    gear = frames.get("Gear", [])
    session_time = frames.get("SessionTime", [])

    step = max(1, total_frames // 1000)  # ~1000 data points max
    compact = []
    for i in range(0, total_frames, step):
        compact.append({
            "t": round(session_time[i], 2) if i < len(session_time) and session_time[i] is not None else None,
            "throttle": round(throttle[i], 3) if i < len(throttle) and throttle[i] is not None else None,
            "brake": round(brake[i], 3) if i < len(brake) and brake[i] is not None else None,
            "speed": round((speed[i] or 0) * 3.6, 1) if i < len(speed) and speed[i] is not None else None,
            "rpm": int(rpm[i]) if i < len(rpm) and rpm[i] is not None else None,
            "gear": int(gear[i]) if i < len(gear) and gear[i] is not None else None,
            "lap": int(lap_nums[i]) if i < len(lap_nums) and lap_nums[i] is not None else None,
            "dist_pct": round(dist[i], 4) if i < len(dist) and dist[i] is not None else None,
        })

    return {
        "filename": os.path.basename(filepath),
        "car_name": car_name,
        "track_name": track_name,
        "session_date": session_date,
        "lap_count": lap_count,
        "best_lap_time": best_lap_time,
        "avg_lap_time": avg_lap_time,
        "sector_1_best": sector_1_best,
        "sector_2_best": sector_2_best,
        "sector_3_best": sector_3_best,
        "air_temp": round(air_temp, 1) if air_temp else None,
        "track_temp": round(track_temp, 1) if track_temp else None,
        "weather": weather,
        "avg_max_brake": avg_max_brake,
        "avg_throttle_point": avg_throttle_point,
        "coasting_zones": coasting_zones,
        "oversteer_count": oversteer_count,
        "tyre_laps": tyre_laps,
        "raw_json": json.dumps(compact),
        "pb_telemetry": pb_telemetry,
    }
