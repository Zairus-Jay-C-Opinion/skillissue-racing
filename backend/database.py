from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DB_PATH = os.getenv("DB_PATH", "./sim_companion.db")

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
