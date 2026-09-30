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
    "camera_person_hourly_stats": {
        "id",
        "camera_id",
        "hour_start",
        "detection_samples",
        "total_person_count",
        "max_person_count",
        "max_confidence",
        "first_detected_at",
        "last_detected_at",
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


@dataclass(frozen=True)
class MigrationStep:
    """Script tabanli SQLite upgrade adimini ve kapsadigi sema degisimlerini tanimlar."""

    order: int
    filename: str
    entrypoint: str
    schema_changes: dict[str, set[str]]


MIGRATION_REGISTRY: tuple[MigrationStep, ...] = (
    MigrationStep(
        order=10,
        filename="migrate_add_nvr_and_camera_fields.py",
        entrypoint="run",
        schema_changes={
            "nvrs": {"id", "name", "host", "onvif_port", "username", "encrypted_password", "brand", "model", "is_active"},
            "cameras": {"brand", "model", "nvr_id"},
        },
    ),
    MigrationStep(
        order=20,
        filename="migrate_add_camera_ai_settings.py",
        entrypoint="main",
        schema_changes={
            "cameras": {
                "ai_confidence_threshold",
                "ai_iou_threshold",
                "ai_alarm_cooldown_seconds",
                "ai_frame_stride",
                "ai_inference_width",
                "ai_active_start",
                "ai_active_end",
                "ai_roi_polygon",
            },
        },
    ),
    MigrationStep(
        order=30,
        filename="migrate_add_alarm_operation_fields.py",
        entrypoint="main",
        schema_changes={
            "alarms": {
                "assigned_to",
                "operator_note",
                "resolution_reason",
                "severity",
                "false_positive",
                "snapshot_sha256",
                "snapshot_annotated_path",
                "snapshot_annotated_sha256",
            },
        },
    ),
    MigrationStep(
        order=40,
        filename="migrate_add_camera_health_samples.py",
        entrypoint="main",
        schema_changes={
            "camera_health_samples": REQUIRED_SCHEMA["camera_health_samples"],
        },
    ),
)

EXPECTED_MIGRATION_SCRIPTS = tuple(step.filename for step in MIGRATION_REGISTRY)


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
    issues: list[str] = []
    seen_orders: set[int] = set()
    seen_filenames: set[str] = set()

    for step in MIGRATION_REGISTRY:
        if step.order in seen_orders:
            issues.append(f"{step.filename}: tekrar eden migration sirasi {step.order}")
        seen_orders.add(step.order)
        if step.filename in seen_filenames:
            issues.append(f"{step.filename}: tekrar eden migration dosyasi")
        seen_filenames.add(step.filename)

        script_path = os.path.join(BACKEND_DIR, "scripts", step.filename)
        if not os.path.isfile(script_path):
            issues.append(f"{step.filename}: dosya yok")
            continue
        try:
            with open(script_path, encoding="utf-8") as script_file:
                source = script_file.read()
        except OSError as exc:
            issues.append(f"{step.filename}: okunamadi ({exc})")
            continue

        if f"def {step.entrypoint}(" not in source:
            issues.append(f"{step.filename}: {step.entrypoint} entrypoint yok")
        for table, columns in step.schema_changes.items():
            if table not in source:
                issues.append(f"{step.filename}: {table} hedefi gorunmuyor")
            for column in columns:
                if column not in source:
                    issues.append(f"{step.filename}: {table}.{column} sema degisimi gorunmuyor")

    if issues:
        return SetupCheck(
            key="migration_script_inventory",
            ok=False,
            severity="medium",
            message="Migration script envanteri sorunlu: " + "; ".join(issues),
        )
    return SetupCheck(
        "migration_script_inventory",
        True,
        "info",
        f"Migration script envanteri mevcut ve sirali: {len(MIGRATION_REGISTRY)} adim.",
    )


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
