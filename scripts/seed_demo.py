"""
Demo seeder — populates the backend with realistic fake session data.

Run while the backend is running:
    python -m scripts.seed_demo

Or with --no-coaching to skip Gemini calls (useful if you have no API key yet):
    python -m scripts.seed_demo --no-coaching

Creates sessions across the last 3 weeks so Progress page shows trends.
"""

import sys
import json
import random
import argparse
import time
import httpx
from datetime import datetime, timedelta

BASE = "http://localhost:8000"

# Realistic iRacing car + track combos with approximate best-lap windows (seconds)
COMBOS = [
    {
        "car": "Ferrari 296 GT3",
        "track": "Spa-Francorchamps",
        "class": "gt3",
        "pb_window": (139.0, 142.0),   # ~2:19–2:22
        "s_split": (0.32, 0.38, 0.30), # S1/S2/S3 proportions of lap
    },
    {
        "car": "Porsche 992 GT3 R",
        "track": "Nürburgring GP",
        "class": "gt3",
        "pb_window": (116.0, 119.5),
        "s_split": (0.28, 0.40, 0.32),
    },
    {
        "car": "Toyota GR86",
        "track": "Suzuka Circuit",
        "class": "street",
        "pb_window": (128.0, 131.0),
        "s_split": (0.30, 0.35, 0.35),
    },
]

WEATHER_OPTS = ["Dry", "Dry", "Dry", "Wet"]  # mostly dry


def rand(lo, hi, decimals=3):
    return round(random.uniform(lo, hi), decimals)


def make_tyre_laps(car_class: str, lap_count: int) -> list:
    """Generate realistic per-lap tyre temps that warm up over the stint."""
    # Tyre ideal ranges from tyre_advisor.py
    ranges = {
        "gt3":   (80, 105), "gt4": (75, 100), "formula": (85, 110),
        "prototype": (80, 108), "street": (60, 90),
    }
    lo, hi = ranges.get(car_class, (75, 105))
    laps = []
    fl = fr = rl = rr = lo - 10  # cold at the start
    for lap in range(1, lap_count + 1):
        # Temps rise toward ideal then stabilise with small variation
        target = rand(lo + 5, hi - 5)
        fl = round(fl + (target - fl) * 0.3 + rand(-2, 2), 1)
        fr = round(fr + (target - fr) * 0.3 + rand(-2, 2), 1)
        rl = round(rl + (target - rl) * 0.25 + rand(-2, 2), 1)
        rr = round(rr + (target - rr) * 0.25 + rand(-2, 2), 1)
        # Clamp to reasonable range
        fl, fr, rl, rr = [max(40, min(130, t)) for t in (fl, fr, rl, rr)]
        laps.append({
            "lap_number": lap,
            "fl_avg_temp": fl, "fr_avg_temp": fr,
            "rl_avg_temp": rl, "rr_avg_temp": rr,
            "fl_wear": round(1.0 - lap * 0.004, 4),
            "fr_wear": round(1.0 - lap * 0.004, 4),
            "rl_wear": round(1.0 - lap * 0.003, 4),
            "rr_wear": round(1.0 - lap * 0.003, 4),
        })
    return laps


def make_raw_json(best_lap: float, lap_count: int) -> str:
    """Generate a compact subsampled telemetry trace (500 points, ~1 lap worth)."""
    frames = []
    total_dist = best_lap * 1.0
    for i in range(500):
        t = i * (best_lap / 500)
        # Simple sinusoidal speed / throttle / brake pattern
        import math
        phase = (i / 500) * math.pi * 6
        speed = round(100 + 80 * abs(math.sin(phase)), 1)
        throttle = round(max(0, min(1, 0.6 + 0.4 * math.sin(phase))), 3)
        brake = round(max(0, min(1, -0.3 * math.sin(phase + 1.5))), 3)
        frames.append({
            "t": round(t, 2),
            "throttle": throttle,
            "brake": brake,
            "speed": speed,
            "rpm": int(4000 + 4000 * throttle),
            "gear": max(1, min(6, int(speed / 50) + 1)),
            "lap": 1,
            "dist_pct": round(i / 500, 4),
        })
    return json.dumps(frames)


def make_session(combo: dict, session_dt: datetime, previous_best: float | None) -> dict:
    lo, hi = combo["pb_window"]
    s1_r, s2_r, s3_r = combo["s_split"]

    # Lap time improves slightly each week
    best = rand(lo, hi)
    avg = round(best * rand(1.008, 1.025), 4)
    lap_count = random.randint(8, 22)
    s1 = round(best * s1_r, 4)
    s2 = round(best * s2_r, 4)
    s3 = round(best - s1 - s2, 4)

    weather = random.choice(WEATHER_OPTS)
    air_temp = rand(12, 28, 1)
    track_temp = rand(air_temp + 3, air_temp + 18, 1)

    return {
        "filename": f"demo_{combo['car'].replace(' ', '_')}_{session_dt.strftime('%Y%m%d_%H%M%S')}.ibt",
        "car_name": combo["car"],
        "track_name": combo["track"],
        "session_date": session_dt.isoformat(),
        "lap_count": lap_count,
        "best_lap_time": best,
        "avg_lap_time": avg,
        "sector_1_best": s1,
        "sector_2_best": s2,
        "sector_3_best": s3,
        "air_temp": air_temp,
        "track_temp": track_temp,
        "weather": weather,
        "raw_json": make_raw_json(best, lap_count),
        "tyre_laps": make_tyre_laps(combo["class"], lap_count),
    }


def seed(no_coaching: bool):
    # Check backend is reachable
    try:
        httpx.get(f"{BASE}/api/status", timeout=3).raise_for_status()
    except Exception:
        print(f"ERROR: Backend not reachable at {BASE}. Start it first:")
        print("  python -m agent.main   (or just uvicorn backend.main:app)")
        sys.exit(1)

    today = datetime.now()
    sessions_created = 0

    # 4 weeks × 2–3 sessions per combo per week (includes current week)
    for week_offset in range(3, -1, -1):  # 3 weeks ago → this week
        week_start = today - timedelta(weeks=week_offset)
        for combo in COMBOS:
            sessions_this_week = random.randint(2, 3)
            # PB window shrinks each week to simulate improvement
            lo, hi = combo["pb_window"]
            improvement = (3 - week_offset) * rand(0.3, 0.8)
            combo["pb_window"] = (lo - improvement, hi - improvement)

            for _ in range(sessions_this_week):
                day_offset = random.randint(0, 6)
                hour_offset = random.randint(14, 22)
                dt = week_start + timedelta(days=day_offset, hours=hour_offset)
                if dt > today:
                    dt = today - timedelta(hours=1)

                session = make_session(combo, dt, None)
                resp = httpx.post(f"{BASE}/api/sessions", json=session, timeout=30)
                if resp.status_code == 201:
                    sessions_created += 1
                    print(f"  ✓ {combo['car']} @ {combo['track']}  {session['best_lap_time']:.3f}s  ({dt.strftime('%d %b')})")
                    if not no_coaching:
                        # Stay under Gemini free tier: 15 req/min = 1 per 4s
                        time.sleep(5)
                elif resp.status_code == 409:
                    print(f"  ~ already exists: {session['filename']}")
                else:
                    print(f"  ✗ {resp.status_code}: {resp.text[:80]}")

    print(f"\nSeeded {sessions_created} sessions.")

    if no_coaching:
        print("Skipped Gemini coaching (--no-coaching flag).")
    else:
        print("\nCoaching is generated asynchronously — wait ~10s then refresh the dashboard.")

    print(f"\nOpen: http://localhost:8000  (or http://localhost:5173 in dev mode)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-coaching", action="store_true", help="Skip Gemini API calls")
    args = parser.parse_args()
    print("Seeding demo data...\n")
    seed(args.no_coaching)
