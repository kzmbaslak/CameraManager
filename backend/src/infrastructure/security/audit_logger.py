"""Güvenlik açısından önemli kullanıcı aksiyonlarını JSON Lines olarak kaydeder."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

AUDIT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
AUDIT_LOG_PATH = os.path.abspath(os.path.join(AUDIT_DIR, "audit.log"))
AUDIT_ARCHIVE_PREFIX = "audit-"
AUDIT_ARCHIVE_SUFFIX = ".log"
DEFAULT_AUDIT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_AUDIT_RETENTION_DAYS = 180


def _positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s sayisal degil; varsayilan %s kullaniliyor.", name, default)
        return default
    if value < 1:
        logger.warning("%s pozitif olmali; varsayilan %s kullaniliyor.", name, default)
        return default
    return value


def _purge_expired_archives() -> None:
    retention_days = _positive_int_env("AUDIT_RETENTION_DAYS", DEFAULT_AUDIT_RETENTION_DAYS)
    cutoff = time.time() - (retention_days * 24 * 60 * 60)
    for filename in os.listdir(AUDIT_DIR):
        if not (filename.startswith(AUDIT_ARCHIVE_PREFIX) and filename.endswith(AUDIT_ARCHIVE_SUFFIX)):
            continue
        archive_path = os.path.join(AUDIT_DIR, filename)
        try:
            if os.path.isfile(archive_path) and os.path.getmtime(archive_path) < cutoff:
                os.remove(archive_path)
        except OSError as exc:
            logger.warning("Eski audit arsivi temizlenemedi: %s", exc)


def _rotate_audit_log_if_needed() -> None:
    max_bytes = _positive_int_env("AUDIT_MAX_BYTES", DEFAULT_AUDIT_MAX_BYTES)
    if not os.path.isfile(AUDIT_LOG_PATH):
        return
    if os.path.getsize(AUDIT_LOG_PATH) < max_bytes:
        return
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    archive_path = os.path.join(AUDIT_DIR, f"{AUDIT_ARCHIVE_PREFIX}{timestamp}{AUDIT_ARCHIVE_SUFFIX}")
    counter = 1
    while os.path.exists(archive_path):
        archive_path = os.path.join(
            AUDIT_DIR,
            f"{AUDIT_ARCHIVE_PREFIX}{timestamp}-{counter}{AUDIT_ARCHIVE_SUFFIX}",
        )
        counter += 1
    os.replace(AUDIT_LOG_PATH, archive_path)


def write_audit_event(
    action: str,
    actor: str | None = None,
    success: bool = True,
    source_ip: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Audit olayını hassas veri içermeyecek şekilde dosyaya ekler."""
    os.makedirs(AUDIT_DIR, exist_ok=True)
    event = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "action": action,
        "actor": actor,
        "success": success,
        "source_ip": source_ip,
        "metadata": metadata or {},
    }
    try:
        _rotate_audit_log_if_needed()
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
        _purge_expired_archives()
    except OSError as exc:
        logger.warning("Audit log yazılamadı: %s", exc)


def read_audit_events(limit: int = 100) -> list[dict[str, Any]]:
    """Audit log dosyasindan son olaylari yeni eskiden olacak sekilde okur."""
    if not os.path.isfile(AUDIT_LOG_PATH):
        return []
    bounded_limit = max(1, min(limit, 500))
    events: list[dict[str, Any]] = []
    try:
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as file:
            lines = file.readlines()[-bounded_limit:]
    except OSError as exc:
        logger.warning("Audit log okunamadi: %s", exc)
        return []

    for line in reversed(lines):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events
