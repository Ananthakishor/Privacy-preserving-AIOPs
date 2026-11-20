"""
backend/app/database.py
SQLAlchemy database setup.
- Uses SQLite for the hackathon prototype.
- Swap DATABASE_URL in .env to a PostgreSQL URL for production.
"""
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import get_settings

settings = get_settings()

# SQLite needs check_same_thread=False because FastAPI may use multiple threads
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

database_url = make_url(settings.database_url)
if database_url.drivername in ("postgres", "postgresql"):
    database_url = database_url.set(drivername="postgresql+psycopg")

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    hide_parameters=True,
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

    # Import all models so SQLAlchemy discovers them before create_all
    from .models import (  # noqa: F401
        tenant, user, collector, monitored_source,
        telemetry, alert, incident, notification,
        recommendation, heartbeat, transfer_audit, remediation,
        aiops_baseline
    )
    # PostgreSQL holds this transaction lock across simultaneous service starts.
    with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(661902601)"))
        Base.metadata.create_all(bind=conn)
        additions = [
            ("metrics", "data_source", "TEXT DEFAULT 'live'"),
            ("telemetry_events", "data_source", "TEXT DEFAULT 'live'"),
            ("collectors", "buffered_count", "INTEGER DEFAULT 0"),
            ("collectors", "cpu_pct", "REAL DEFAULT 0.0"),
            ("collectors", "mem_pct", "REAL DEFAULT 0.0"),
        ]
        inspector = inspect(conn)
        indexes = {item["name"] for item in inspector.get_indexes("aiops_baselines")}
        if "ix_baseline_source_cat" in indexes:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_baseline_tenant_source_cat "
                              "ON aiops_baselines (tenant_id, source_id, category)"))
            conn.execute(text("DROP INDEX ix_baseline_source_cat"))
        for table, column, definition in additions:
            if column not in {item["name"] for item in inspector.get_columns(table)}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
