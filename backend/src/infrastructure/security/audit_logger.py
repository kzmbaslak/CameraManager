"""Güvenlik açısından önemli kullanıcı aksiyonlarını JSON Lines olarak kaydeder."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

AUDIT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
AUDIT_LOG_PATH = os.path.abspath(os.path.join(AUDIT_DIR, "audit.log"))


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
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("Audit log yazılamadı: %s", exc)
