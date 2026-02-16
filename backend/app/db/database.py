"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Get settings from environment
DATABASE_URL_ENV = os.getenv("DATABASE_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

def _default_sqlite_url() -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return f"sqlite:///{os.path.join(data_dir, 'app.db')}"

if not DATABASE_URL_ENV:
    if ENVIRONMENT == "production":
        raise RuntimeError("DATABASE_URL must be set when ENVIRONMENT=production")
    DATABASE_URL_ENV = _default_sqlite_url()

upload_dir = os.getenv("UPLOAD_DIR", "./uploads")

class Settings:
    database_url = DATABASE_URL_ENV
    upload_dir = upload_dir

settings = Settings()

engine_kwargs = {"echo": os.getenv("SQL_ECHO", "false").strip().lower() == "true"}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

