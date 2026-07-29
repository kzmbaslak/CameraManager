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
EXPECTED_MIGRATION_SCRIPTS = (
    "migrate_add_nvr_and_camera_fields.py",
    "migrate_add_camera_ai_settings.py",
    "migrate_add_alarm_operation_fields.py",
    "migrate_add_camera_health_samples.py",
)

REQUIRED_SCHEMA: dict[str, set[str]] = {
    "cameras": {
        "id",
        "name",
        "host",
        "rtsp_port",
        "onvif_port",
        "username",
        "encrypted_password",
        "password_updated_at",
        "rtsp_path",
        "status",
        "motion_detection_enabled",
        "ai_detection_enabled",
        "ai_confidence_threshold",
        "ai_iou_threshold",
        "ai_alarm_cooldown_seconds",
        "ai_frame_stride",
        "ai_inference_width",
        "ai_active_start",
        "ai_active_end",
        "ai_roi_polygon",
        "brand",
        "model",
        "nvr_id",
        "site",
        "building",
        "floor",
        "zone",
        "onvif_ptz_supported",
        "onvif_capabilities_checked_at",
        "continuous_recording_enabled",
    },
    "nvrs": {"id", "name", "host", "onvif_port", "username", "encrypted_password", "password_updated_at", "brand", "model", "is_active"},
    "alarms": {
        "id",
        "camera_id",
        "alarm_type",
        "status",
        "confidence",
        "snapshot_path",
        "snapshot_sha256",
        "snapshot_annotated_path",
        "snapshot_annotated_sha256",
        "severity",
        "false_positive",
        "assigned_to",
        "operator_note",
        "resolution_reason",
    },
    "users": {"id", "username", "password_hash", "role", "is_active"},
    "camera_health_samples": {"id", "camera_id", "checked_at", "reachable", "status", "latency_ms", "failure_reason"},
    "camera_stream_metrics": {
        "id",
        "camera_id",
        "sampled_at",
        "producer_running",
        "subscriber_count",
        "current_broadcast_fps",
        "average_ai_inference_ms",
        "host_cpu_load_percent",
        "host_memory_used_percent",
        "reconnects",
        "open_failures",
        "failure_count",
    },
    "recording_segments": {
        "id",
        "camera_id",
        "started_at",
        "ended_at",
        "recording_type",
        "status",
        "file_path",
        "file_sha256",
        "size_bytes",
        "codec",
        "width",
        "height",
        "fps",
        "alarm_id",
        "created_at",
    },
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


def _migration_script_inventory_check() -> SetupCheck:
    missing_scripts = [
        script
        for script in EXPECTED_MIGRATION_SCRIPTS
        if not os.path.isfile(os.path.join(BACKEND_DIR, "scripts", script))
    ]
    if missing_scripts:
        return SetupCheck(
            key="migration_script_inventory",
            ok=False,
            severity="medium",
            message="Migration script envanteri eksik: " + ", ".join(missing_scripts),
        )
    return SetupCheck("migration_script_inventory", True, "info", "Migration script envanteri mevcut.")


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
        _migration_script_inventory_check(),
    ]
    return checks
