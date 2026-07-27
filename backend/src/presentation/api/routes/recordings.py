"""Video kayit segmentleri API endpoint'leri."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.application.use_cases.recording_use_cases import RecordingUseCases
from src.domain.entities.recording_segment import RecordingSegment
from src.infrastructure.recording.retention import RecordingRetentionService
from src.infrastructure.security.audit_logger import write_audit_event
from src.presentation.api.dependencies import (
    get_recording_manage_user,
    get_recording_segment_repository,
    get_recording_use_cases,
    get_recording_view_user,
)
from src.presentation.api.schemas.recording_schema import (
    RecordingPruneResponse,
    RecordingSegmentListResponse,
    RecordingSegmentResponse,
)


router = APIRouter(prefix="/recordings", tags=["Recordings"])


def _segment_response(segment: RecordingSegment) -> RecordingSegmentResponse:
    duration = None
    if segment.ended_at is not None:
        duration = round((segment.ended_at - segment.started_at).total_seconds(), 3)
    return RecordingSegmentResponse(
        id=segment.id or 0,
        camera_id=segment.camera_id,
        started_at=segment.started_at,
        ended_at=segment.ended_at,
        recording_type=segment.recording_type,
        status=segment.status,
        filename=os.path.basename(segment.file_path),
        duration_seconds=duration,
        file_sha256=segment.file_sha256,
        size_bytes=segment.size_bytes,
        codec=segment.codec,
        width=segment.width,
        height=segment.height,
        fps=segment.fps,
        alarm_id=segment.alarm_id,
        created_at=segment.created_at,
    )


@router.get("/", response_model=RecordingSegmentListResponse)
def list_recording_segments(
    camera_id: Optional[int] = Query(default=None, gt=0),
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(default=100, ge=1, le=500),
    use_cases: RecordingUseCases = Depends(get_recording_use_cases),
    current_user: dict = Depends(get_recording_view_user),
):
    """Kayit segmentlerini kamera ve zaman araligina gore dosya yolu sizdirmadan listeler."""
    segments = list(use_cases.list_segments(camera_id=camera_id, since=since, until=until, limit=limit))
    return RecordingSegmentListResponse(
        items=[_segment_response(segment) for segment in segments],
        total=len(segments),
        limit=limit,
    )


@router.post("/maintenance/prune", response_model=RecordingPruneResponse)
def prune_recording_segments(
    retention_days: Optional[int] = Query(default=None, ge=1, le=3650),
    quota_mb: Optional[int] = Query(default=None, ge=0, le=10_000_000),
    repository=Depends(get_recording_segment_repository),
    current_user: dict = Depends(get_recording_manage_user),
):
    """Kayit retention/disk kotasi temizligini admin yetkisiyle calistirir."""
    result = RecordingRetentionService(repository).prune(retention_days=retention_days, quota_mb=quota_mb)
    write_audit_event(
        "recording.prune",
        actor=current_user.get("sub"),
        metadata={
            "retention_days": result.retention_days,
            "quota_mb": result.quota_mb,
            "removed_count": result.removed_count,
            "removed_bytes": result.removed_bytes,
            "deleted_db_count": result.deleted_db_count,
            "skipped_count": result.skipped_count,
        },
    )
    return RecordingPruneResponse(
        retention_days=result.retention_days,
        quota_mb=result.quota_mb,
        removed_count=result.removed_count,
        removed_bytes=result.removed_bytes,
        deleted_db_count=result.deleted_db_count,
        skipped_count=result.skipped_count,
        removed_filenames=result.removed_filenames,
        skipped_reasons=result.skipped_reasons,
    )
