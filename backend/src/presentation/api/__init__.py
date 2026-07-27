"""API ana router'i, saglik ve guvenlik durusu endpoint'leri."""

import os
from datetime import timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.infrastructure.database.database import get_db
from src.infrastructure.database.models import CameraModel, NVRModel
from src.infrastructure.setup.preflight import collect_setup_checks
from src.infrastructure.security.runtime_config import require_camera_encryption_key, require_jwt_secret
from src.infrastructure.time_utils import utc_now
from src.presentation.api.dependencies import get_current_user, get_role_permissions, get_security_status_user
from src.presentation.api.routes.alarms import router as alarms_router
from src.presentation.api.routes.audit import router as audit_router
from src.presentation.api.routes.auth import router as auth_router
from src.presentation.api.routes.backups import router as backups_router
from src.presentation.api.routes.cameras import router as cameras_router
from src.presentation.api.routes.nvrs import router as nvrs_router
from src.presentation.api.routes.streams import router as streams_router
from src.presentation.api.routes.users import router as users_router

router = APIRouter()


@router.get("/health")
def health_check():
    """Sistemin ayakta olup olmadigini kontrol eder."""
    return {"status": "healthy"}


@router.get("/health/ready")
def readiness_check(response: Response):
    """Servis monitorleri icin hassas detay sizdirmayan hazirlik kontrolu."""
    checks = collect_setup_checks()
    public_checks = [
        {"key": check.key, "ok": check.ok, "severity": check.severity}
        for check in checks
    ]
    blocking_issues = [
        check
        for check in checks
        if not check.ok and check.severity in {"critical", "high"}
    ]
    warnings = [check for check in checks if not check.ok and check.severity not in {"critical", "high"}]
    ready = len(blocking_issues) == 0
    if not ready:
        response.status_code = 503
    return {
        "status": "ready" if ready else "degraded",
        "ready": ready,
        "blocking_issue_count": len(blocking_issues),
        "warning_count": len(warnings),
        "checks": public_checks,
    }


@router.get("/security/posture")
def security_posture(
    current_user: dict = Depends(get_security_status_user),
    db: Session = Depends(get_db),
):
    """Uygulamanin temel guvenlik durusunu operator icin ozetler."""
    findings = []
    cors_origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    trusted_hosts = [
        host.strip()
        for host in os.environ.get("TRUSTED_HOSTS", "").split(",")
        if host.strip()
    ]

    jwt_ok = True
    encryption_ok = True
    try:
        require_jwt_secret()
    except RuntimeError as exc:
        jwt_ok = False
        findings.append({"severity": "critical", "message": str(exc)})
    try:
        require_camera_encryption_key()
    except RuntimeError as exc:
        encryption_ok = False
        findings.append({"severity": "critical", "message": str(exc)})

    if "*" in cors_origins:
        findings.append({"severity": "high", "message": "CORS_ALLOWED_ORIGINS wildcard (*) icermemeli."})
    if not cors_origins:
        findings.append({"severity": "medium", "message": "CORS_ALLOWED_ORIGINS acikca tanimlanmali."})
    trusted_hosts_configured = bool(trusted_hosts) and "*" not in trusted_hosts
    if not trusted_hosts_configured:
        findings.append({"severity": "medium", "message": "TRUSTED_HOSTS uretim host/IP listesiyle sinirlandirilmali."})

    https_enabled = os.environ.get("HTTPS_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    if not https_enabled:
        findings.append({"severity": "medium", "message": "Uretim ortaminda HTTPS_ENABLED=true ve TLS terminasyonu kullanilmali."})

    secure_cookie_auth = os.environ.get("AUTH_COOKIE_MODE", "").strip().lower() == "secure"
    if not secure_cookie_auth:
        findings.append({"severity": "medium", "message": "JWT icin HttpOnly/SameSite secure cookie veya refresh flow eklenmeli."})

    audit_chain_secret_configured = len(os.environ.get("AUDIT_CHAIN_SECRET", "").strip()) >= 32
    if not audit_chain_secret_configured:
        findings.append({"severity": "medium", "message": "Audit zinciri icin AUDIT_CHAIN_SECRET en az 32 karakter olarak tanimlanmali."})

    app_log_dir = os.environ.get("APP_LOG_DIR", "logs").strip()
    try:
        app_log_backup_count = int(os.environ.get("APP_LOG_BACKUP_COUNT", "5") or "0")
    except ValueError:
        app_log_backup_count = 0
    app_log_rotation_configured = bool(app_log_dir) and app_log_backup_count > 0
    app_log_json_format = os.environ.get("APP_LOG_FORMAT", "text").strip().lower() == "json"
    app_log_sensitive_query_masking = True
    if not app_log_rotation_configured:
        findings.append({"severity": "medium", "message": "APP_LOG_DIR ve APP_LOG_BACKUP_COUNT ile uygulama log rotasyonu tanimlanmali."})

    try:
        device_password_rotation_days = int(os.environ.get("DEVICE_PASSWORD_ROTATION_DAYS", "90") or "90")
    except ValueError:
        device_password_rotation_days = 90
        findings.append({"severity": "medium", "message": "DEVICE_PASSWORD_ROTATION_DAYS sayisal olmali."})
    device_password_rotation_days = min(max(device_password_rotation_days, 30), 365)
    password_cutoff = utc_now() - timedelta(days=device_password_rotation_days)
    camera_password_filter = CameraModel.encrypted_password.isnot(None) & (CameraModel.encrypted_password != "")
    nvr_password_filter = NVRModel.encrypted_password.isnot(None) & (NVRModel.encrypted_password != "")
    camera_password_device_count = db.query(CameraModel).filter(camera_password_filter).count()
    nvr_password_device_count = db.query(NVRModel).filter(nvr_password_filter).count()
    overdue_camera_password_count = (
        db.query(CameraModel)
        .filter(camera_password_filter)
        .filter(or_(CameraModel.password_updated_at.is_(None), CameraModel.password_updated_at < password_cutoff))
        .count()
    )
    overdue_nvr_password_count = (
        db.query(NVRModel)
        .filter(nvr_password_filter)
        .filter(or_(NVRModel.password_updated_at.is_(None), NVRModel.password_updated_at < password_cutoff))
        .count()
    )
    missing_camera_rotation_count = (
        db.query(CameraModel)
        .filter(camera_password_filter)
        .filter(CameraModel.password_updated_at.is_(None))
        .count()
    )
    missing_nvr_rotation_count = (
        db.query(NVRModel)
        .filter(nvr_password_filter)
        .filter(NVRModel.password_updated_at.is_(None))
        .count()
    )
    overdue_device_password_count = overdue_camera_password_count + overdue_nvr_password_count
    missing_device_password_rotation_count = missing_camera_rotation_count + missing_nvr_rotation_count
    if overdue_device_password_count > 0:
        findings.append({
            "severity": "high",
            "message": (
                f"{overdue_device_password_count} kamera/NVR parolasi "
                f"{device_password_rotation_days} gunluk rotasyon politikasini asti."
            ),
        })

    audit_webhook_url = os.environ.get("AUDIT_WEBHOOK_URL", "").strip()
    audit_webhook_configured = False
    if audit_webhook_url:
        parsed_webhook = urlparse(audit_webhook_url)
        audit_webhook_configured = parsed_webhook.scheme == "https" and bool(parsed_webhook.netloc)
        if not audit_webhook_configured:
            findings.append({"severity": "medium", "message": "AUDIT_WEBHOOK_URL HTTPS ve geceri bir merkezi log endpoint'i olmali."})
    else:
        findings.append({"severity": "low", "message": "Kurumsal ortamda AUDIT_WEBHOOK_URL ile merkezi/SIEM audit arsivi tanimlanmali."})

    setup_checks = [
        {"key": check.key, "ok": check.ok, "severity": check.severity, "message": check.message}
        for check in collect_setup_checks()
    ]
    for check in setup_checks:
        if not check["ok"]:
            findings.append({"severity": check["severity"], "message": check["message"]})

    return {
        "status": "attention" if findings else "hardened",
        "jwt_secret_configured": jwt_ok,
        "camera_encryption_key_configured": encryption_ok,
        "cors_origins_configured": bool(cors_origins) and "*" not in cors_origins,
        "trusted_hosts_configured": trusted_hosts_configured,
        "https_enabled": https_enabled,
        "secure_cookie_auth": secure_cookie_auth,
        "audit_chain_secret_configured": audit_chain_secret_configured,
        "audit_webhook_configured": audit_webhook_configured,
        "app_log_rotation_configured": app_log_rotation_configured,
        "app_log_json_format": app_log_json_format,
        "app_log_sensitive_query_masking": app_log_sensitive_query_masking,
        "device_password_rotation_days": device_password_rotation_days,
        "device_password_rotation_compliant": overdue_device_password_count == 0,
        "device_password_total_count": camera_password_device_count + nvr_password_device_count,
        "overdue_device_password_count": overdue_device_password_count,
        "missing_device_password_rotation_count": missing_device_password_rotation_count,
        "overdue_camera_password_count": overdue_camera_password_count,
        "overdue_nvr_password_count": overdue_nvr_password_count,
        "security_headers_enabled": True,
        "content_security_policy_enabled": True,
        "setup_checks": setup_checks,
        "stream_token_transport": "websocket_first_message",
        "stream_token_ttl_seconds": 60,
        "findings": findings,
    }


@router.get("/security/permissions")
def security_permissions(current_user: dict = Depends(get_current_user)):
    """Mevcut kullanicinin rol ve politika izinlerini dondurur."""
    permissions = sorted(get_role_permissions(current_user.get("role")))
    return {
        "role": current_user.get("role"),
        "permissions": permissions,
    }


@router.get("/setup/status")
def setup_status(current_user: dict = Depends(get_security_status_user)):
    """Kurulum dosyasi, model, DB semasi ve admin hazirligini raporlar."""
    checks = [
        {"key": check.key, "ok": check.ok, "severity": check.severity, "message": check.message}
        for check in collect_setup_checks()
    ]
    return {
        "ready": all(check["ok"] for check in checks),
        "checks": checks,
    }


router.include_router(cameras_router)
router.include_router(alarms_router)
router.include_router(audit_router)
router.include_router(backups_router)
router.include_router(users_router)
router.include_router(streams_router)
router.include_router(nvrs_router)
router.include_router(auth_router)
