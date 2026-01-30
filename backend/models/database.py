"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from config import get_settings

settings = get_settings()

# Use asyncpg for async if needed; for simplicity we use sync with psycopg2
engine = create_engine(
    settings.database_url.replace("postgresql://", "postgresql+psycopg2://"),
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for FastAPI: yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    from .signal import Signal  # noqa: F401
    Base.metadata.create_all(bind=engine)
