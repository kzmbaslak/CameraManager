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
    import hashlib
    import sqlite3

    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "", 1)
    columns = {
        "ai_confidence_threshold": "REAL DEFAULT 0.5",
        "ai_iou_threshold": "REAL DEFAULT 0.45",
        "ai_alarm_cooldown_seconds": "INTEGER DEFAULT 60",
        "ai_frame_stride": "INTEGER DEFAULT 1",
        "ai_inference_width": "INTEGER DEFAULT 640",
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
        "severity": "TEXT DEFAULT 'medium'",
        "false_positive": "BOOLEAN DEFAULT 0",
        "snapshot_sha256": "TEXT",
        "snapshot_annotated_path": "TEXT",
        "snapshot_annotated_sha256": "TEXT",
    }
    conn = sqlite3.connect(db_path)
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(alarms)").fetchall()}
        for column, definition in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE alarms ADD COLUMN {column} {definition}")
        rows = conn.execute(
            "SELECT id, snapshot_path FROM alarms WHERE snapshot_path IS NOT NULL AND snapshot_sha256 IS NULL"
        ).fetchall()
        for alarm_id, snapshot_path in rows:
            if not snapshot_path:
                continue
            absolute_path = os.path.abspath(snapshot_path)
            if not os.path.isfile(absolute_path):
                continue
            with open(absolute_path, "rb") as file:
                snapshot_sha256 = hashlib.sha256(file.read()).hexdigest()
            conn.execute(
                "UPDATE alarms SET snapshot_sha256 = ? WHERE id = ?",
                (snapshot_sha256, alarm_id),
            )
        conn.commit()
    finally:
        conn.close()


def ensure_device_password_rotation_columns() -> None:
    """Eski SQLite kurulumlarinda cihaz parola rotasyonu kolonlarini idempotent ekler."""
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        return
    import sqlite3

    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "", 1)
    conn = sqlite3.connect(db_path)
    try:
        for table in ("cameras", "nvrs"):
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if "password_updated_at" not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN password_updated_at DATETIME")
            conn.execute(
                f"""
                UPDATE {table}
                SET password_updated_at = COALESCE(updated_at, created_at)
                WHERE encrypted_password IS NOT NULL
                  AND encrypted_password != ''
                  AND password_updated_at IS NULL
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_camera_location_columns() -> None:
    """Eski SQLite kurulumlarinda kamera saha/konum kolonlarini idempotent ekler."""
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        return
    import sqlite3

    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "", 1)
    columns = {
        "site": "TEXT",
        "building": "TEXT",
        "floor": "TEXT",
        "zone": "TEXT",
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


def ensure_camera_stream_metrics_table() -> None:
    """Eski SQLite kurulumlarinda stream metrikleri tablosunu idempotent olusturur."""
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        return
    import sqlite3

    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "", 1)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS camera_stream_metrics (
                id INTEGER PRIMARY KEY,
                camera_id INTEGER,
                sampled_at DATETIME,
                producer_running BOOLEAN DEFAULT 0,
                subscriber_count INTEGER DEFAULT 0,
                current_broadcast_fps REAL,
                average_ai_inference_ms REAL,
                host_cpu_load_percent REAL,
                host_memory_used_percent REAL,
                reconnects INTEGER DEFAULT 0,
                open_failures INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                FOREIGN KEY(camera_id) REFERENCES cameras(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS ix_camera_stream_metrics_id ON camera_stream_metrics (id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_camera_stream_metrics_camera_id ON camera_stream_metrics (camera_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_camera_stream_metrics_sampled_at ON camera_stream_metrics (sampled_at)")
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
