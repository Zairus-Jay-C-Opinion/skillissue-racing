"""
Backfill lap_telemetry for existing PersonalBest records.

This only needs to be run once. After the fix, new PBs automatically
get their lap_telemetry written by create_session.

Run while the backend is NOT running (direct DB access):
    python -m scripts.fix_pb_telemetry

Or with the backend running it also works — SQLite allows concurrent reads.
"""

import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from backend.database import SessionLocal
from backend.models import PersonalBest, Session as SessionModel, Setting
from agent.ibt_parser import parse_ibt


def _telemetry_folder(db) -> Path:
    row = db.query(Setting).filter_by(key="telemetry_folder").first()
    if row and row.value:
        return Path(row.value)
    return Path.home() / "Documents" / "iRacing" / "telemetry"


def main():
    db = SessionLocal()
    try:
        pbs = db.query(PersonalBest).filter(PersonalBest.lap_telemetry == None).all()

        if not pbs:
            print("All PB records already have lap_telemetry. Nothing to do.")
            return

        print(f"Found {len(pbs)} PB record(s) missing lap_telemetry.\n")
        telemetry_dir = _telemetry_folder(db)

        updated = 0
        for pb in pbs:
            print(f"  {pb.car_name} @ {pb.track_name}")

            # Find the session that set this PB
            session = db.query(SessionModel).filter_by(id=pb.session_id).first()
            if not session:
                print(f"    ✗ Session {pb.session_id} not found in DB — skipping\n")
                continue

            ibt_path = telemetry_dir / session.filename
            if not ibt_path.exists():
                print(f"    ✗ IBT file not found: {ibt_path} — skipping\n")
                continue

            print(f"    Parsing {ibt_path.name} ...")
            result = parse_ibt(str(ibt_path))
            if result is None:
                print(f"    ✗ Parse failed — skipping\n")
                continue

            trace = result.get("pb_telemetry")
            if not trace:
                print(f"    ✗ No pb_telemetry extracted (no valid laps?) — skipping\n")
                continue

            pb.lap_telemetry = trace
            db.commit()
            point_count = len(json.loads(trace))
            print(f"    ✓ Saved {point_count} trace points\n")
            updated += 1

        print(f"Done. Updated {updated}/{len(pbs)} PB record(s).")
        if updated < len(pbs):
            print("Skipped records need their IBT files present in the telemetry folder.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
