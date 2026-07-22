"""Kurulum bütünlüğü için dosya, model ve veritabanı kontrolleri."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy import inspect

from src.domain.entities.user import UserRole
from src.infrastructure.database.database import SessionLocal, engine
from src.infrastructure.database.models import UserModel


BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ENV_PATH = os.path.join(BACKEND_DIR, ".env")
MODEL_PATH = os.path.join(BACKEND_DIR, "models", "yolov8n.onnx")

REQUIRED_SCHEMA: dict[str, set[str]] = {
    "cameras": {
        "id",
        "name",
        "host",
        "rtsp_port",
        "onvif_port",
        "username",
        "encrypted_password",
        "rtsp_path",
        "status",
        "motion_detection_enabled",
        "ai_detection_enabled",
        "ai_confidence_threshold",
        "ai_iou_threshold",
        "ai_alarm_cooldown_seconds",
        "ai_active_start",
        "ai_active_end",
        "ai_roi_polygon",
        "brand",
        "model",
        "nvr_id",
    },
    "nvrs": {"id", "name", "host", "onvif_port", "username", "encrypted_password", "brand", "model", "is_active"},
    "alarms": {
        "id",
        "camera_id",
        "alarm_type",
        "status",
        "confidence",
        "snapshot_path",
        "snapshot_sha256",
        "severity",
        "false_positive",
        "assigned_to",
        "operator_note",
        "resolution_reason",
    },
    "users": {"id", "username", "password_hash", "role", "is_active"},
    "camera_health_samples": {"id", "camera_id", "checked_at", "reachable", "status", "latency_ms", "failure_reason"},
}


@dataclass(frozen=True)
class SetupCheck:
    """Tek bir kurulum kontrolünün sonucunu taşır."""

    key: str
    ok: bool
    severity: str
    message: str


def _schema_check() -> SetupCheck:
    inspector = inspect(engine)
    missing_parts: list[str] = []
    table_names = set(inspector.get_table_names())
    for table, required_columns in REQUIRED_SCHEMA.items():
        if table not in table_names:
            missing_parts.append(f"{table} tablosu")
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table)}
        missing_columns = sorted(required_columns - existing_columns)
        if missing_columns:
            missing_parts.append(f"{table}: {', '.join(missing_columns)}")
    if missing_parts:
        return SetupCheck(
            key="database_schema",
            ok=False,
            severity="high",
            message="Veritabani semasi eksik: " + "; ".join(missing_parts),
        )
    return SetupCheck("database_schema", True, "info", "Veritabani semasi guncel.")


def _active_admin_check() -> SetupCheck:
    db = SessionLocal()
    try:
        exists = (
            db.query(UserModel)
            .filter(UserModel.role == UserRole.ADMIN, UserModel.is_active.is_(True))
            .first()
            is not None
        )
    finally:
        db.close()
    if not exists:
        return SetupCheck(
            key="active_admin",
            ok=False,
            severity="high",
            message="Aktif admin kullanici yok; INITIAL_ADMIN_* veya scripts/create_user.py ile admin olusturun.",
        )
    return SetupCheck("active_admin", True, "info", "Aktif admin kullanici var.")


def collect_setup_checks() -> list[SetupCheck]:
    """Kurulumun çalışmaya hazır olup olmadığını gösteren kontrolleri döndürür."""
    env_file_present = os.path.isfile(ENV_PATH)
    model_present = os.path.isfile(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 1024 * 1024
    checks = [
        SetupCheck(
            key="env_file",
            ok=env_file_present,
            severity="low",
            message=".env dosyasi mevcut." if env_file_present else ".env dosyasi yok; degerler sistem env ile gelmiyorsa kurulum eksik kalir.",
        ),
        SetupCheck(
            key="ai_model",
            ok=model_present,
            severity="high",
            message="YOLO ONNX modeli mevcut." if model_present else "backend/models/yolov8n.onnx modeli yok veya beklenenden kucuk.",
        ),
        _schema_check(),
        _active_admin_check(),
    ]
    return checks
