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
    """
    Create all tables and apply lightweight migrations for existing databases.

    SQLAlchemy's create_all() only creates MISSING tables — it never alters
    existing ones. When we add a new column to a model (e.g. metrics.data_source),
    an existing on-disk DB will be missing that column and cause HTTP 500 errors.

    This function runs `ALTER TABLE ... ADD COLUMN` for every known new column
    so the live DB stays in sync with the ORM models without a full drop/recreate.
    """
    import logging
    log = logging.getLogger(__name__)

    # Import all models so SQLAlchemy discovers them before create_all
    from .models import (  # noqa: F401
        tenant, user, collector, monitored_source,
        telemetry, alert, incident, notification,
        recommendation, heartbeat, transfer_audit, remediation,
        aiops_baseline
    )
    # Create any tables that don't exist yet
    Base.metadata.create_all(bind=engine)

    # ── Incremental migrations for existing databases ──────────────────────
    # Each entry: (table_name, column_name, column_definition)
    # Safe to run repeatedly — skipped if column already exists.
    _MIGRATIONS = [
        ("metrics",           "data_source",    "TEXT DEFAULT 'live'"),
        ("telemetry_events",  "data_source",    "TEXT DEFAULT 'live'"),
        ("collectors",        "buffered_count", "INTEGER DEFAULT 0"),
        ("collectors",        "cpu_pct",        "REAL DEFAULT 0.0"),
        ("collectors",        "mem_pct",        "REAL DEFAULT 0.0"),
    ]

    # Only run migrations on SQLite (ALTER TABLE is simpler there)
    if settings.database_url.startswith("sqlite"):
        import sqlite3
        # Extract the file path from the URL (strip sqlite:/// or sqlite://./)
        db_path = settings.database_url.replace("sqlite:///", "").replace("sqlite://./", "./")
        try:
            conn = sqlite3.connect(db_path)
            for table, column, definition in _MIGRATIONS:
                # Check if column already exists
                existing = [
                    row[1]
                    for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
                ]
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                    conn.commit()
                    log.info(f"[MIGRATION] Added column {table}.{column}")
            conn.close()
        except Exception as e:
            log.warning(f"[MIGRATION] Migration step failed (non-fatal): {e}")
