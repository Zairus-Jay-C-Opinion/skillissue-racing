import os
import json
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func, desc

from backend.database import get_db, init_db
from backend.models import (
    Session as SessionModel,
    CoachingResult,
    TyreData,
    PersonalBest,
    WeeklyNarrative,
    Setting,
)
from backend.tyre_advisor import analyse_tyre_data
from backend import gemini

app = FastAPI(title="Sim Racing Companion", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    _seed_default_settings()
    _load_gemini_key_from_db()


def _seed_default_settings():
    from backend.database import SessionLocal
    db = SessionLocal()
    defaults = {
        "telemetry_folder": os.path.expanduser("~/Documents/iRacing/telemetry"),
        "setups_watch_folder": os.path.expanduser("~/Downloads/iRacing-setups"),
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "onboarding_complete": "false",
        "overlay_position_x": "960",
        "overlay_position_y": "40",
    }
    for k, v in defaults.items():
        if not db.query(Setting).filter_by(key=k).first():
            db.add(Setting(key=k, value=v))
    db.commit()
    db.close()


def _load_gemini_key_from_db():
    """
    If the user saved a Gemini key via the Settings UI, it lives in the DB.
    On every startup we read it back into os.environ so gemini.py can find it,
    even after uvicorn restarts. The .env file takes priority if set there.
    """
    from backend.database import SessionLocal
    db = SessionLocal()
    row = db.query(Setting).filter_by(key="gemini_api_key").first()
    db.close()
    if row and row.value and not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = row.value
        print("[startup] Gemini API key loaded from database.")


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    filename: str
    car_name: str
    track_name: str
    session_date: str
    lap_count: Optional[int] = None
    best_lap_time: Optional[float] = None
    avg_lap_time: Optional[float] = None
    sector_1_best: Optional[float] = None
    sector_2_best: Optional[float] = None
    sector_3_best: Optional[float] = None
    air_temp: Optional[float] = None
    track_temp: Optional[float] = None
    weather: Optional[str] = None
    raw_json: Optional[str] = None
    tyre_laps: Optional[list] = None


class SettingUpdate(BaseModel):
    value: str


class GeminiTestRequest(BaseModel):
    key: str


# ── Sessions ─────────────────────────────────────────────────────────────────

@app.post("/api/sessions", status_code=201)
async def create_session(body: SessionCreate, background_tasks: BackgroundTasks, db: DBSession = Depends(get_db)):
    if db.query(SessionModel).filter_by(filename=body.filename).first():
        raise HTTPException(status_code=409, detail="Session already exists")

    session_id = str(uuid.uuid4())
    session_dt = datetime.fromisoformat(body.session_date)

    session = SessionModel(
        id=session_id,
        filename=body.filename,
        car_name=body.car_name,
        track_name=body.track_name,
        session_date=session_dt,
        lap_count=body.lap_count,
        best_lap_time=body.best_lap_time,
        avg_lap_time=body.avg_lap_time,
        sector_1_best=body.sector_1_best,
        sector_2_best=body.sector_2_best,
        sector_3_best=body.sector_3_best,
        air_temp=body.air_temp,
        track_temp=body.track_temp,
        weather=body.weather,
        raw_json=body.raw_json,
    )
    db.add(session)

    # Update personal best
    pb = db.query(PersonalBest).filter_by(car_name=body.car_name, track_name=body.track_name).first()
    if body.best_lap_time:
        if pb is None or body.best_lap_time < pb.best_lap_time:
            if pb is None:
                pb = PersonalBest(
                    id=str(uuid.uuid4()),
                    car_name=body.car_name,
                    track_name=body.track_name,
                )
                db.add(pb)
            pb.best_lap_time = body.best_lap_time
            pb.session_id = session_id
            pb.updated_at = datetime.utcnow()

    # Store per-lap tyre data
    if body.tyre_laps:
        for lap in body.tyre_laps:
            analysis = analyse_tyre_data(
                body.car_name,
                lap.get("fl_avg_temp", 0),
                lap.get("fr_avg_temp", 0),
                lap.get("rl_avg_temp", 0),
                lap.get("rr_avg_temp", 0),
            )
            db.add(TyreData(
                id=str(uuid.uuid4()),
                session_id=session_id,
                lap_number=lap.get("lap_number"),
                fl_avg_temp=lap.get("fl_avg_temp"),
                fr_avg_temp=lap.get("fr_avg_temp"),
                rl_avg_temp=lap.get("rl_avg_temp"),
                rr_avg_temp=lap.get("rr_avg_temp"),
                fl_wear=lap.get("fl_wear"),
                fr_wear=lap.get("fr_wear"),
                rl_wear=lap.get("rl_wear"),
                rr_wear=lap.get("rr_wear"),
                temp_imbalance_front=analysis["imbalance_front"],
                temp_imbalance_rear=analysis["imbalance_rear"],
                recommendation=analysis["recommendation"],
            ))

    db.commit()

    # Fire coaching in background — FastAPI runs this after the response is sent
    background_tasks.add_task(_run_coaching_bg, session_id, body)

    return {"id": session_id}


async def _run_coaching_bg(session_id: str, body: SessionCreate):
    """
    Background task: calls Gemini and stores the coaching result.
    Uses its own DB session (the request's session is already closed by now).
    Failures are logged but never re-raised — a missing coaching result is
    shown gracefully in the UI.
    """
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        pb = db.query(PersonalBest).filter_by(car_name=body.car_name, track_name=body.track_name).first()
        delta_to_pb = None
        if pb and body.best_lap_time:
            delta_to_pb = round(body.best_lap_time - pb.best_lap_time, 3)

        tyre_rows = db.query(TyreData).filter_by(session_id=session_id).all()
        fl_avg = sum(r.fl_avg_temp for r in tyre_rows if r.fl_avg_temp) / max(len(tyre_rows), 1)
        fr_avg = sum(r.fr_avg_temp for r in tyre_rows if r.fr_avg_temp) / max(len(tyre_rows), 1)
        rl_avg = sum(r.rl_avg_temp for r in tyre_rows if r.rl_avg_temp) / max(len(tyre_rows), 1)
        rr_avg = sum(r.rr_avg_temp for r in tyre_rows if r.rr_avg_temp) / max(len(tyre_rows), 1)

        session_data = {
            "car_name": body.car_name,
            "track_name": body.track_name,
            "air_temp": body.air_temp,
            "track_temp": body.track_temp,
            "weather": body.weather,
            "best_lap_time": body.best_lap_time,
            "avg_lap_time": body.avg_lap_time,
            "lap_count": body.lap_count,
            "delta_to_pb": delta_to_pb,
            "fl_temp_avg": round(fl_avg, 1),
            "fr_temp_avg": round(fr_avg, 1),
            "rl_temp_avg": round(rl_avg, 1),
            "rr_temp_avg": round(rr_avg, 1),
            "temp_imbalance": round(abs(fl_avg - fr_avg), 1),
        }

        result = await gemini.generate_coaching(session_data)
        tips = result.get("tips", [{}, {}, {}])
        coaching = CoachingResult(
            id=str(uuid.uuid4()),
            session_id=session_id,
            headline=result.get("headline", ""),
            tip_1_title=tips[0].get("title", "") if len(tips) > 0 else "",
            tip_1_detail=tips[0].get("detail", "") if len(tips) > 0 else "",
            tip_2_title=tips[1].get("title", "") if len(tips) > 1 else "",
            tip_2_detail=tips[1].get("detail", "") if len(tips) > 1 else "",
            tip_3_title=tips[2].get("title", "") if len(tips) > 2 else "",
            tip_3_detail=tips[2].get("detail", "") if len(tips) > 2 else "",
        )
        db.add(coaching)
        db.commit()
        print(f"[coaching] Generated for session {session_id}")
    except Exception as e:
        print(f"[coaching] Gemini call failed for {session_id}: {e}")
    finally:
        db.close()


@app.get("/api/sessions")
def list_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    car: Optional[str] = None,
    track: Optional[str] = None,
    db: DBSession = Depends(get_db),
):
    q = db.query(SessionModel)
    if car:
        q = q.filter(SessionModel.car_name.ilike(f"%{car}%"))
    if track:
        q = q.filter(SessionModel.track_name.ilike(f"%{track}%"))
    total = q.count()
    sessions = q.order_by(desc(SessionModel.session_date)).offset((page - 1) * limit).limit(limit).all()

    items = []
    for s in sessions:
        pb = db.query(PersonalBest).filter_by(car_name=s.car_name, track_name=s.track_name).first()
        delta = None
        if pb and s.best_lap_time:
            delta = round(s.best_lap_time - pb.best_lap_time, 3)
        items.append({
            "id": s.id,
            "filename": s.filename,
            "car_name": s.car_name,
            "track_name": s.track_name,
            "session_date": s.session_date.isoformat() if s.session_date else None,
            "lap_count": s.lap_count,
            "best_lap_time": s.best_lap_time,
            "avg_lap_time": s.avg_lap_time,
            "delta_to_pb": delta,
        })
    return {"total": total, "page": page, "items": items}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    s = db.query(SessionModel).filter_by(id=session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    pb = db.query(PersonalBest).filter_by(car_name=s.car_name, track_name=s.track_name).first()
    delta = None
    if pb and s.best_lap_time:
        delta = round(s.best_lap_time - pb.best_lap_time, 3)
    return {
        "id": s.id,
        "filename": s.filename,
        "car_name": s.car_name,
        "track_name": s.track_name,
        "session_date": s.session_date.isoformat() if s.session_date else None,
        "lap_count": s.lap_count,
        "best_lap_time": s.best_lap_time,
        "avg_lap_time": s.avg_lap_time,
        "sector_1_best": s.sector_1_best,
        "sector_2_best": s.sector_2_best,
        "sector_3_best": s.sector_3_best,
        "air_temp": s.air_temp,
        "track_temp": s.track_temp,
        "weather": s.weather,
        "delta_to_pb": delta,
        "raw_json": json.loads(s.raw_json) if s.raw_json else None,
    }


@app.get("/api/sessions/{session_id}/coaching")
def get_coaching(session_id: str, db: DBSession = Depends(get_db)):
    c = db.query(CoachingResult).filter_by(session_id=session_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="No coaching result yet")
    return {
        "headline": c.headline,
        "tips": [
            {"title": c.tip_1_title, "detail": c.tip_1_detail},
            {"title": c.tip_2_title, "detail": c.tip_2_detail},
            {"title": c.tip_3_title, "detail": c.tip_3_detail},
        ],
    }


@app.get("/api/sessions/{session_id}/tyres")
def get_tyres(session_id: str, db: DBSession = Depends(get_db)):
    rows = db.query(TyreData).filter_by(session_id=session_id).order_by(TyreData.lap_number).all()
    return [
        {
            "lap_number": r.lap_number,
            "fl_avg_temp": r.fl_avg_temp,
            "fr_avg_temp": r.fr_avg_temp,
            "rl_avg_temp": r.rl_avg_temp,
            "rr_avg_temp": r.rr_avg_temp,
            "fl_wear": r.fl_wear,
            "fr_wear": r.fr_wear,
            "rl_wear": r.rl_wear,
            "rr_wear": r.rr_wear,
            "temp_imbalance_front": r.temp_imbalance_front,
            "temp_imbalance_rear": r.temp_imbalance_rear,
            "recommendation": r.recommendation,
        }
        for r in rows
    ]


# ── Personal bests ────────────────────────────────────────────────────────────

@app.get("/api/pbs")
def list_pbs(db: DBSession = Depends(get_db)):
    pbs = db.query(PersonalBest).order_by(PersonalBest.updated_at.desc()).all()
    return [
        {
            "car_name": p.car_name,
            "track_name": p.track_name,
            "best_lap_time": p.best_lap_time,
            "session_id": p.session_id,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in pbs
    ]


@app.get("/api/pbs/{car}/{track}")
def get_pb(car: str, track: str, db: DBSession = Depends(get_db)):
    pb = db.query(PersonalBest).filter_by(car_name=car, track_name=track).first()
    if not pb:
        raise HTTPException(status_code=404, detail="No PB for this car/track")
    return {
        "car_name": pb.car_name,
        "track_name": pb.track_name,
        "best_lap_time": pb.best_lap_time,
        "session_id": pb.session_id,
        "lap_telemetry": json.loads(pb.lap_telemetry) if pb.lap_telemetry else None,
        "updated_at": pb.updated_at.isoformat() if pb.updated_at else None,
    }


# ── Progress / weekly narratives ──────────────────────────────────────────────

@app.get("/api/progress/narrative")
def list_narratives(db: DBSession = Depends(get_db)):
    rows = db.query(WeeklyNarrative).order_by(desc(WeeklyNarrative.week_start)).all()
    return [
        {
            "id": r.id,
            "week_start": r.week_start.isoformat(),
            "week_end": r.week_end.isoformat(),
            "narrative_text": r.narrative_text,
            "delta_seconds": r.delta_seconds,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@app.post("/api/progress/generate")
async def generate_narrative(db: DBSession = Depends(get_db)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start - timedelta(days=1)

    def week_sessions(start, end):
        return db.query(SessionModel).filter(
            SessionModel.session_date >= datetime.combine(start, datetime.min.time()),
            SessionModel.session_date <= datetime.combine(end, datetime.max.time()),
        ).all()

    this_week = week_sessions(week_start, week_end)
    last_week = week_sessions(prev_week_start, prev_week_end)

    if not this_week:
        raise HTTPException(status_code=400, detail="No sessions this week to report on")

    # Find most common car/track
    from collections import Counter
    car_counts = Counter(s.car_name for s in this_week)
    track_counts = Counter(s.track_name for s in this_week)
    top_car = car_counts.most_common(1)[0][0]
    top_track = track_counts.most_common(1)[0][0]

    this_best = min((s.best_lap_time for s in this_week if s.best_lap_time), default=None)
    last_best = min((s.best_lap_time for s in last_week if s.best_lap_time), default=None)
    delta = round(this_best - last_best, 3) if this_best and last_best else None
    direction = "faster" if delta and delta < 0 else "slower"

    stats = {
        "delta": abs(delta) if delta else "N/A",
        "direction": direction,
        "s1_trend": "improved" if delta and delta < 0 else "similar",
        "s2_trend": "similar",
        "s3_trend": "similar",
        "tyre_consistency": "same",
        "session_count": len(this_week),
        "top_car": top_car,
        "top_track": top_track,
    }

    narrative = await gemini.generate_weekly_narrative(stats)

    row = WeeklyNarrative(
        id=str(uuid.uuid4()),
        week_start=week_start,
        week_end=week_end,
        narrative_text=narrative,
        delta_seconds=delta,
    )
    db.add(row)
    db.commit()
    return {"narrative": narrative}


# ── Settings ──────────────────────────────────────────────────────────────────

@app.get("/api/settings")
def get_settings(db: DBSession = Depends(get_db)):
    rows = db.query(Setting).all()
    result = {r.key: r.value for r in rows}
    # Never expose the API key to the frontend
    if "gemini_api_key" in result:
        result["gemini_api_key"] = "••••••••" if result["gemini_api_key"] else ""
    return result


@app.put("/api/settings/{key}")
def update_setting(key: str, body: SettingUpdate, db: DBSession = Depends(get_db)):
    row = db.query(Setting).filter_by(key=key).first()
    if row is None:
        row = Setting(key=key, value=body.value)
        db.add(row)
    else:
        row.value = body.value
    # Sync Gemini key to env so gemini.py picks it up without restart
    if key == "gemini_api_key":
        os.environ["GEMINI_API_KEY"] = body.value
    db.commit()
    return {"key": key, "value": "••••••••" if key == "gemini_api_key" else body.value}


# ── Status ────────────────────────────────────────────────────────────────────

@app.get("/api/status")
def status():
    import psutil
    iracing_running = any("iracingsim" in p.name().lower() for p in psutil.process_iter(["name"]))
    return {"backend": "ok", "iracing_running": iracing_running}


# ── Gemini key test ───────────────────────────────────────────────────────────

@app.post("/api/gemini/test")
async def test_gemini(body: GeminiTestRequest):
    result = await gemini.test_api_key(body.key)
    if result["ok"]:
        return {"valid": True}
    raise HTTPException(status_code=400, detail=result["error"])


# ── Serve built frontend ──────────────────────────────────────────────────────

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")
