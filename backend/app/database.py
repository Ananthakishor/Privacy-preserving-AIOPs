"""
backend/app/database.py
SQLAlchemy database setup.
- Uses SQLite for the hackathon prototype.
- Swap DATABASE_URL in .env to a PostgreSQL URL for production.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import get_settings

settings = get_settings()

# SQLite needs check_same_thread=False because FastAPI may use multiple threads
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,  # Set True to log SQL queries during debugging
)

# Enable WAL mode for SQLite — better concurrent read performance
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All ORM models inherit from this Base
Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined in ORM models. Called at app startup."""
    # Import all models here so SQLAlchemy discovers them before create_all
    from .models import (  # noqa: F401
        tenant, user, collector, monitored_source,
        telemetry, alert, incident, notification,
        recommendation, heartbeat, transfer_audit, remediation
    )
    Base.metadata.create_all(bind=engine)
