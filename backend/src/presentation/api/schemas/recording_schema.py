"""Video kayit segmentleri API semalari."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RecordingSegmentResponse(BaseModel):
    """Kayit segmentini dosya yolu sizdirmadan donduren yanit."""

    id: int
    camera_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    recording_type: str
    status: str
    filename: str
    duration_seconds: Optional[float] = None
    file_sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    alarm_id: Optional[int] = None
    created_at: Optional[datetime] = None

class RecordingSegmentListResponse(BaseModel):
    """Kayit segmenti liste yaniti."""

    items: list[RecordingSegmentResponse]
    total: int
    limit: int


class RecordingPruneResponse(BaseModel):
    """Kayit retention/kota temizligi sonucu."""

    retention_days: int
    quota_mb: int
    removed_count: int
    removed_bytes: int
    deleted_db_count: int
    skipped_count: int
    removed_filenames: list[str]
    skipped_reasons: list[str]
