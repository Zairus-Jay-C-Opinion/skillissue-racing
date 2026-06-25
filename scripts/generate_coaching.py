"""
Generates coaching for sessions that don't have it yet.

Run while the backend is running:
    python -m scripts.generate_coaching          # all missing sessions
    python -m scripts.generate_coaching --limit 1  # just one session

Calls Gemini one session at a time, synchronously, with a 10s gap between
calls to stay under the free tier limit of 15 req/min.
"""

import sys
import time
import argparse
import httpx
from pathlib import Path

BASE = "http://localhost:8000"
DELAY = 10  # seconds between successful Gemini calls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max sessions to generate coaching for")
    args = parser.parse_args()
    # Check backend is reachable
    try:
        httpx.get(f"{BASE}/api/status", timeout=3).raise_for_status()
    except Exception:
        print("ERROR: Backend not reachable. Start it first:")
        print("  uvicorn backend.main:app --reload --port 8000")
        sys.exit(1)

    # Get all sessions (paginate because the endpoint caps at 100 per page)
    sessions = []
    page = 1
    while True:
        resp = httpx.get(f"{BASE}/api/sessions?limit=100&page={page}", timeout=10)
        data = resp.json()
        sessions.extend(data["items"])
        if len(sessions) >= data["total"]:
            break
        page += 1
    print(f"Found {len(sessions)} sessions total.\n")

    done = 0
    skipped = 0
    failed = 0

    for s in sessions:
        if args.limit is not None and done >= args.limit:
            break
        sid = s["id"]
        label = f"{s['car_name']} @ {s['track_name']} ({s['session_date'][:10]})"

        # Check if coaching already exists
        check = httpx.get(f"{BASE}/api/sessions/{sid}/coaching", timeout=5)
        if check.status_code == 200:
            print(f"  ~ already has coaching: {label}")
            skipped += 1
            continue

        # Fetch full session detail (list endpoint omits air_temp, track_temp, weather)
        detail_resp = httpx.get(f"{BASE}/api/sessions/{sid}", timeout=5)
        detail = detail_resp.json() if detail_resp.status_code == 200 else {}

        # Build session_data for coaching prompt (same fields as _run_coaching_bg)
        tyre_resp = httpx.get(f"{BASE}/api/sessions/{sid}/tyres", timeout=5)
        tyre_rows = tyre_resp.json() if tyre_resp.status_code == 200 else []

        fl = sum(r["fl_avg_temp"] for r in tyre_rows if r.get("fl_avg_temp")) / max(len(tyre_rows), 1)
        fr = sum(r["fr_avg_temp"] for r in tyre_rows if r.get("fr_avg_temp")) / max(len(tyre_rows), 1)
        rl = sum(r["rl_avg_temp"] for r in tyre_rows if r.get("rl_avg_temp")) / max(len(tyre_rows), 1)
        rr = sum(r["rr_avg_temp"] for r in tyre_rows if r.get("rr_avg_temp")) / max(len(tyre_rows), 1)

        delta = detail.get("delta_to_pb")

        session_data = {
            "car_name": s["car_name"],
            "track_name": s["track_name"],
            "air_temp": detail.get("air_temp"),
            "track_temp": detail.get("track_temp"),
            "weather": detail.get("weather"),
            "best_lap_time": s.get("best_lap_time"),
            "avg_lap_time": s.get("avg_lap_time"),
            "lap_count": s.get("lap_count"),
            "delta_to_pb": delta,
            "fl_temp_avg": round(fl, 1),
            "fr_temp_avg": round(fr, 1),
            "rl_temp_avg": round(rl, 1),
            "rr_temp_avg": round(rr, 1),
            "temp_imbalance": round(abs(fl - fr), 1),
        }

        print(f"  > Generating: {label} ...", end=" ", flush=True)

        # Call Gemini via a small inline helper (sync, with retry)
        result = _call_gemini_sync(session_data)
        if result is None:
            print("FAILED (Gemini error — will retry next run)")
            failed += 1
            time.sleep(DELAY)
            continue

        # Save to DB by posting directly via SQLAlchemy
        _save_coaching(sid, result)
        print("OK")
        done += 1
        time.sleep(DELAY)

    print(f"\nDone. Generated: {done}  Skipped: {skipped}  Failed: {failed}")
    if failed:
        print("Re-run this script to retry failed sessions.")


def _call_gemini_sync(session_data: dict) -> dict | None:
    """Synchronous Gemini call with simple retry on 429/503."""
    import os, json
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        print("\nERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"

    prompt = f"""You are an expert sim racing coach. Give exactly 3 specific, actionable coaching tips for this session. Be direct. No generic advice.

Car: {session_data.get('car_name')} | Track: {session_data.get('track_name')}
Conditions: {session_data.get('air_temp')}°C air, {session_data.get('track_temp')}°C track, {session_data.get('weather')}
Best lap: {session_data.get('best_lap_time')}s | Avg: {session_data.get('avg_lap_time')}s | Laps: {session_data.get('lap_count')}
Delta to PB: {session_data.get('delta_to_pb')}s
Tyre temps — FL:{session_data.get('fl_temp_avg')} FR:{session_data.get('fr_temp_avg')} RL:{session_data.get('rl_temp_avg')} RR:{session_data.get('rr_temp_avg')}°C | Imbalance: {session_data.get('temp_imbalance')}°C

Respond with exactly this JSON:
{{"tips":[{{"title":"...","detail":"..."}},{{"title":"...","detail":"..."}},{{"title":"...","detail":"..."}}],"headline":"..."}}"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    delays = [15, 30, 65]  # 65s covers a full RPM window on the last retry

    for attempt, delay in enumerate([0] + delays):
        if delay:
            print(f"\n    [429] waiting {delay}s...", end=" ", flush=True)
            time.sleep(delay)
        try:
            resp = httpx.post(url, json=payload, timeout=30)
        except Exception as e:
            print(f"\n    [network error] {e}")
            continue

        if resp.status_code in (429, 503):
            try:
                err_body = resp.json().get("error", {})
                err_msg = err_body.get("message", resp.text[:120])
            except Exception:
                err_msg = resp.text[:120]
            print(f"\n    [{resp.status_code}] {err_msg[:160]}", end="")
            if attempt < len(delays):
                continue
            return None

        if resp.status_code != 200:
            print(f"\n    [HTTP {resp.status_code}] {resp.text[:120]}")
            return None

        body = resp.json()
        candidates = body.get("candidates", [])
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return None
        raw = parts[0].get("text", "").strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(raw)
        except Exception:
            return None

    return None


def _save_coaching(session_id: str, result: dict):
    """Write coaching result directly to SQLite via SQLAlchemy."""
    import uuid, os
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

    os.environ.setdefault("DB_PATH", str(Path(__file__).parent.parent / "sim_companion.db"))

    from backend.database import SessionLocal
    from backend.models import CoachingResult

    tips = result.get("tips", [{}, {}, {}])
    db = SessionLocal()
    # Remove existing if any
    db.query(CoachingResult).filter_by(session_id=session_id).delete()
    db.add(CoachingResult(
        id=str(uuid.uuid4()),
        session_id=session_id,
        headline=result.get("headline", ""),
        tip_1_title=tips[0].get("title", "") if len(tips) > 0 else "",
        tip_1_detail=tips[0].get("detail", "") if len(tips) > 0 else "",
        tip_2_title=tips[1].get("title", "") if len(tips) > 1 else "",
        tip_2_detail=tips[1].get("detail", "") if len(tips) > 1 else "",
        tip_3_title=tips[2].get("title", "") if len(tips) > 2 else "",
        tip_3_detail=tips[2].get("detail", "") if len(tips) > 2 else "",
    ))
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
