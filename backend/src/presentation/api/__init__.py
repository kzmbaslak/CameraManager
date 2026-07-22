"""API ana router'i, saglik ve guvenlik durusu endpoint'leri."""

import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends

from src.infrastructure.security.runtime_config import require_camera_encryption_key, require_jwt_secret
from src.presentation.api.dependencies import get_operator_user
from src.presentation.api.routes.alarms import router as alarms_router
from src.presentation.api.routes.audit import router as audit_router
from src.presentation.api.routes.auth import router as auth_router
from src.presentation.api.routes.cameras import router as cameras_router
from src.presentation.api.routes.nvrs import router as nvrs_router
from src.presentation.api.routes.streams import router as streams_router
from src.presentation.api.routes.users import router as users_router

router = APIRouter()


@router.get("/health")
def health_check():
    """Sistemin ayakta olup olmadigini kontrol eder."""
    return {"status": "healthy"}


@router.get("/security/posture")
def security_posture(current_user: dict = Depends(get_operator_user)):
    """Uygulamanin temel guvenlik durusunu operator icin ozetler."""
    findings = []
    cors_origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
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

    https_enabled = os.environ.get("HTTPS_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    if not https_enabled:
        findings.append({"severity": "medium", "message": "Uretim ortaminda HTTPS_ENABLED=true ve TLS terminasyonu kullanilmali."})

    secure_cookie_auth = os.environ.get("AUTH_COOKIE_MODE", "").strip().lower() == "secure"
    if not secure_cookie_auth:
        findings.append({"severity": "medium", "message": "JWT icin HttpOnly/SameSite secure cookie veya refresh flow eklenmeli."})

    audit_chain_secret_configured = len(os.environ.get("AUDIT_CHAIN_SECRET", "").strip()) >= 32
    if not audit_chain_secret_configured:
        findings.append({"severity": "medium", "message": "Audit zinciri icin AUDIT_CHAIN_SECRET en az 32 karakter olarak tanimlanmali."})

    audit_webhook_url = os.environ.get("AUDIT_WEBHOOK_URL", "").strip()
    audit_webhook_configured = False
    if audit_webhook_url:
        parsed_webhook = urlparse(audit_webhook_url)
        audit_webhook_configured = parsed_webhook.scheme == "https" and bool(parsed_webhook.netloc)
        if not audit_webhook_configured:
            findings.append({"severity": "medium", "message": "AUDIT_WEBHOOK_URL HTTPS ve geceri bir merkezi log endpoint'i olmali."})
    else:
        findings.append({"severity": "low", "message": "Kurumsal ortamda AUDIT_WEBHOOK_URL ile merkezi/SIEM audit arsivi tanimlanmali."})

    return {
        "status": "attention" if findings else "hardened",
        "jwt_secret_configured": jwt_ok,
        "camera_encryption_key_configured": encryption_ok,
        "cors_origins_configured": bool(cors_origins) and "*" not in cors_origins,
        "https_enabled": https_enabled,
        "secure_cookie_auth": secure_cookie_auth,
        "audit_chain_secret_configured": audit_chain_secret_configured,
        "audit_webhook_configured": audit_webhook_configured,
        "stream_token_transport": "websocket_first_message",
        "stream_token_ttl_seconds": 60,
        "findings": findings,
    }


router.include_router(cameras_router)
router.include_router(alarms_router)
router.include_router(audit_router)
router.include_router(users_router)
router.include_router(streams_router)
router.include_router(nvrs_router)
router.include_router(auth_router)
