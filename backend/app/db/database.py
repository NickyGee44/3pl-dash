"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Get settings from environment
database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/3pl_audit")
upload_dir = os.getenv("UPLOAD_DIR", "./uploads")

class Settings:
    database_url = database_url
    upload_dir = upload_dir

settings = Settings()

engine = create_engine(settings.database_url, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


