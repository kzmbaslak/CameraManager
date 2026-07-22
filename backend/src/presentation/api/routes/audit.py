"""Audit log goruntuleme endpoint'leri."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.infrastructure.security.audit_logger import read_audit_events
from src.presentation.api.dependencies import get_admin_user

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditEventResponse(BaseModel):
    timestamp: str
    action: str
    actor: str | None = None
    success: bool = True
    source_ip: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/events", response_model=list[AuditEventResponse])
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_admin_user),
):
    """Admin kullanicilar icin son audit olaylarini listeler."""
    return read_audit_events(limit=limit)
