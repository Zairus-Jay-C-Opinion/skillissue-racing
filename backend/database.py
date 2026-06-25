from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import sys
from pathlib import Path


def _default_db_path() -> str:
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle — store DB in AppData so it
        # persists across updates and isn't inside the temp extraction dir
        app_data = os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        data_dir = Path(app_data) / "SkillIssueRacing"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir / "sim_companion.db")
    return "./sim_companion.db"


DB_PATH = os.getenv("DB_PATH", _default_db_path())

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Models are imported in main.py before this is called, registering
    # all tables with Base.metadata. We just create them here.
    Base.metadata.create_all(bind=engine)
