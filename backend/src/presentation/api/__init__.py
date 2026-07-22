"""API ana router'i, saglik ve guvenlik durusu endpoint'leri."""

import os

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

    return {
        "status": "attention" if findings else "hardened",
        "jwt_secret_configured": jwt_ok,
        "camera_encryption_key_configured": encryption_ok,
        "cors_origins_configured": bool(cors_origins) and "*" not in cors_origins,
        "https_enabled": https_enabled,
        "secure_cookie_auth": secure_cookie_auth,
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
