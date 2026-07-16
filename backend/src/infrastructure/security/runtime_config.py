"""Çalışma zamanı güvenlik yapılandırmasını doğrulayan yardımcılar."""

from __future__ import annotations

import base64
import os


PLACEHOLDER_MARKERS = ("BURAYA_", "dev-only", "change-in-production")


def _has_placeholder(value: str) -> bool:
    """Env değerinin örnek/placeholder olup olmadığını kontrol eder."""
    return any(marker in value for marker in PLACEHOLDER_MARKERS)


def require_jwt_secret() -> str:
    """JWT imzalama anahtarını üretim güvenliği için zorunlu olarak döner."""
    value = os.environ.get("JWT_SECRET_KEY", "").strip()
    if not value or _has_placeholder(value) or len(value) < 32:
        raise RuntimeError("JWT_SECRET_KEY en az 32 karakterlik gerçek bir gizli anahtar olmalıdır.")
    return value


def require_camera_encryption_key() -> bytes:
    """Kamera/NVR şifreleme anahtarını base64 32 bayt olarak doğrular."""
    raw = os.environ.get("CAMERA_ENCRYPTION_KEY", "").strip()
    if not raw or _has_placeholder(raw):
        raise RuntimeError("CAMERA_ENCRYPTION_KEY base64 kodlu 32 bayt gerçek anahtar olmalıdır.")
    try:
        key = base64.b64decode(raw)
    except Exception as exc:
        raise RuntimeError("CAMERA_ENCRYPTION_KEY geçerli base64 olmalıdır.") from exc
    if len(key) != 32:
        raise RuntimeError("CAMERA_ENCRYPTION_KEY çözüldüğünde 32 bayt olmalıdır.")
    return key


def validate_security_environment() -> None:
    """Uygulama başlamadan kritik güvenlik env değerlerini doğrular."""
    require_jwt_secret()
    require_camera_encryption_key()
