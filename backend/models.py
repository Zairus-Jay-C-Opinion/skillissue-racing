from sqlalchemy import Column, Text, Integer, Float, DateTime, Date, ForeignKey, func, UniqueConstraint
from backend.database import Base
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Text, primary_key=True, default=gen_uuid)
    filename = Column(Text, unique=True, nullable=False)
    car_name = Column(Text, nullable=False)
    track_name = Column(Text, nullable=False)
    session_date = Column(DateTime, nullable=False)
    lap_count = Column(Integer)
    best_lap_time = Column(Float)
    avg_lap_time = Column(Float)
    sector_1_best = Column(Float)
    sector_2_best = Column(Float)
    sector_3_best = Column(Float)
    air_temp = Column(Float)
    track_temp = Column(Float)
    weather = Column(Text)
    raw_json = Column(Text)
    created_at = Column(DateTime, default=func.now())


class CoachingResult(Base):
    __tablename__ = "coaching_results"

    id = Column(Text, primary_key=True, default=gen_uuid)
    session_id = Column(Text, ForeignKey("sessions.id"))
    headline = Column(Text)
    tip_1_title = Column(Text)
    tip_1_detail = Column(Text)
    tip_2_title = Column(Text)
    tip_2_detail = Column(Text)
    tip_3_title = Column(Text)
    tip_3_detail = Column(Text)
    created_at = Column(DateTime, default=func.now())


class TyreData(Base):
    __tablename__ = "tyre_data"

    id = Column(Text, primary_key=True, default=gen_uuid)
    session_id = Column(Text, ForeignKey("sessions.id"))
    lap_number = Column(Integer)
    fl_avg_temp = Column(Float)
    fr_avg_temp = Column(Float)
    rl_avg_temp = Column(Float)
    rr_avg_temp = Column(Float)
    fl_wear = Column(Float)
    fr_wear = Column(Float)
    rl_wear = Column(Float)
    rr_wear = Column(Float)
    temp_imbalance_front = Column(Float)
    temp_imbalance_rear = Column(Float)
    recommendation = Column(Text)


class PersonalBest(Base):
    __tablename__ = "personal_bests"

    id = Column(Text, primary_key=True, default=gen_uuid)
    car_name = Column(Text, nullable=False)
    track_name = Column(Text, nullable=False)
    best_lap_time = Column(Float, nullable=False)
    session_id = Column(Text, ForeignKey("sessions.id"))
    lap_telemetry = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("car_name", "track_name"),)


class WeeklyNarrative(Base):
    __tablename__ = "weekly_narratives"

    id = Column(Text, primary_key=True, default=gen_uuid)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    narrative_text = Column(Text, nullable=False)
    delta_seconds = Column(Float)
    created_at = Column(DateTime, default=func.now())


class Setting(Base):
    __tablename__ = "settings"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
