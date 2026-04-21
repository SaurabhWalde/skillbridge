"""
DATABASE CONNECTION
───────────────────
SQLAlchemy engine + session factory + dependency for FastAPI.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency — yields a DB session per request.
    yield = give session to endpoint
    finally = close session after response is sent (guaranteed cleanup)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()