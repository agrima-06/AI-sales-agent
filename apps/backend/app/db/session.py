from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Setup pool sizes for production performance
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
from app.models.base import Base


def get_db() -> Generator:
    """
    FastAPI Dependency injection provider for database sessions.
    Guarantees cleanup and rollback on errors.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
