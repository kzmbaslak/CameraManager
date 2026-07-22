"""
SQLite veritabanı bağlantı yapılandırması.

NullPool kullanılır: SQLite dosya tabanlıdır, bağlantı açmak ucuzdur.
QueuePool (varsayılan) WebSocket akışları + thread havuzu kombinasyonunda
"pool overflow" hatasına yol açar; NullPool bunu ortadan kaldırır.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
os.makedirs(DB_DIR, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'nvr_system.db')}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,  # her Session bağımsız bağlantı — pool tükenmesi yok
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_camera_ai_settings_columns() -> None:
    """Eski SQLite kurulumlarinda kamera AI ayarlari kolonlarini idempotent ekler."""
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        return
    import sqlite3

    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "", 1)
    columns = {
        "ai_confidence_threshold": "REAL DEFAULT 0.5",
        "ai_iou_threshold": "REAL DEFAULT 0.45",
        "ai_alarm_cooldown_seconds": "INTEGER DEFAULT 60",
        "ai_active_start": "TEXT",
        "ai_active_end": "TEXT",
        "ai_roi_polygon": "TEXT",
    }
    conn = sqlite3.connect(db_path)
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(cameras)").fetchall()}
        for column, definition in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE cameras ADD COLUMN {column} {definition}")
        conn.commit()
    finally:
        conn.close()


def ensure_alarm_operation_columns() -> None:
    """Eski SQLite kurulumlarinda alarm operasyon kolonlarini idempotent ekler."""
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        return
    import sqlite3

    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "", 1)
    columns = {
        "assigned_to": "TEXT",
        "operator_note": "TEXT",
        "resolution_reason": "TEXT",
    }
    conn = sqlite3.connect(db_path)
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(alarms)").fetchall()}
        for column, definition in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE alarms ADD COLUMN {column} {definition}")
        conn.commit()
    finally:
        conn.close()


def get_db():
    """FastAPI dependency — request başına bir DB session açar, biter bitmez kapatır."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
