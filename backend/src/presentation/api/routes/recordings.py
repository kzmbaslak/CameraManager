"""Video kayit segmentleri API endpoint'leri."""

from __future__ import annotations

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from src.application.use_cases.recording_use_cases import RecordingUseCases
from src.domain.entities.recording_segment import RecordingSegment
from src.infrastructure.recording.retention import RecordingRetentionService, recording_storage_dir
from src.infrastructure.security.audit_logger import write_audit_event
from src.presentation.api.dependencies import (
    get_recording_manage_user,
    get_recording_segment_repository,
    get_recording_use_cases,
    get_recording_view_user,
)
from src.presentation.api.schemas.recording_schema import (
    RecordingPruneResponse,
    RecordingDetectionItem,
    RecordingMetadataResponse,
    RecordingSegmentListResponse,
    RecordingSegmentResponse,
)


router = APIRouter(prefix="/recordings", tags=["Recordings"])


def _safe_recording_file_path(segment: RecordingSegment, storage_root: Path | None = None) -> Path:
    """Kayit dosyasini storage kok dizini disina cikmadan cozer."""
    root = (storage_root or recording_storage_dir()).resolve()
    path = Path(segment.file_path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kayit dosyasi guvenli depolama dizini disinda.",
        )
    if segment.status != "complete" or segment.ended_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kayit segmenti henuz tamamlanmamis.",
        )
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayit dosyasi bulunamadi.")
    return path


def _recording_metadata_response(
    segment: RecordingSegment,
    storage_root: Path | None = None,
) -> RecordingMetadataResponse:
    """Kayit metadata sidecar'ini guvenli storage siniri icinde okur."""
    path = _safe_recording_file_path(segment, storage_root)
    metadata_path = path.with_suffix(".detections.json")
    if not metadata_path.is_file():
        return RecordingMetadataResponse(
            segment_id=segment.id or 0,
            camera_id=segment.camera_id,
            alarm_id=segment.alarm_id,
            frame_width=segment.width,
            frame_height=segment.height,
            detected_at=None,
            detections=[],
            motion=None,
            tamper=None,
        )
    try:
        with open(metadata_path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        payload = {}
    detections = []
    for item in payload.get("detections") or []:
        box = item.get("bounding_box") if isinstance(item, dict) else None
        if not isinstance(box, dict):
            continue
        try:
            detections.append(RecordingDetectionItem(
                label=str(item.get("label") or "person"),
                confidence=float(item.get("confidence") or 0),
                bounding_box={
                    "x": int(box.get("x") or 0),
                    "y": int(box.get("y") or 0),
                    "width": int(box.get("width") or 0),
                    "height": int(box.get("height") or 0),
                },
            ))
        except (TypeError, ValueError):
            continue
    detected_at = payload.get("detected_at")
    if isinstance(detected_at, str) and detected_at.endswith("Z"):
        detected_at = detected_at[:-1] + "+00:00"
    motion = None
    motion_payload = payload.get("motion")
    if isinstance(motion_payload, dict):
        try:
            changed_ratio = float(motion_payload.get("changed_ratio") or 0)
            changed_percent = float(motion_payload.get("changed_percent") or (changed_ratio * 100))
            motion = {
                "changed_ratio": min(max(changed_ratio, 0.0), 1.0),
                "changed_percent": min(max(changed_percent, 0.0), 100.0),
            }
        except (TypeError, ValueError):
            motion = None
    tamper = None
    tamper_payload = payload.get("tamper")
    if isinstance(tamper_payload, dict):
        try:
            tamper = {
                "reason": str(tamper_payload.get("reason") or "unknown"),
                "brightness_mean": float(tamper_payload.get("brightness_mean") or 0),
                "brightness_stddev": float(tamper_payload.get("brightness_stddev") or 0),
                "blur_variance": float(tamper_payload.get("blur_variance") or 0),
            }
        except (TypeError, ValueError):
            tamper = None
    return RecordingMetadataResponse(
        segment_id=segment.id or 0,
        camera_id=segment.camera_id,
        alarm_id=segment.alarm_id,
        frame_width=payload.get("frame_width") or segment.width,
        frame_height=payload.get("frame_height") or segment.height,
        detected_at=detected_at,
        detections=detections,
        motion=motion,
        tamper=tamper,
    )


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
    alarm_id: Optional[int] = Query(default=None, gt=0),
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(default=100, ge=1, le=500),
    use_cases: RecordingUseCases = Depends(get_recording_use_cases),
    current_user: dict = Depends(get_recording_view_user),
):
    """Kayit segmentlerini alarm, kamera ve zaman araligina gore dosya yolu sizdirmadan listeler."""
    if alarm_id is not None:
        segments = list(use_cases.list_alarm_segments(alarm_id))
        if camera_id is not None:
            segments = [segment for segment in segments if segment.camera_id == camera_id]
        if since is not None:
            segments = [segment for segment in segments if segment.started_at >= since]
        if until is not None:
            segments = [segment for segment in segments if segment.started_at <= until]
        segments = segments[:limit]
    else:
        segments = list(use_cases.list_segments(camera_id=camera_id, since=since, until=until, limit=limit))
    return RecordingSegmentListResponse(
        items=[_segment_response(segment) for segment in segments],
        total=len(segments),
        limit=limit,
    )


@router.get("/{segment_id}/file")
def get_recording_file(
    segment_id: int,
    use_cases: RecordingUseCases = Depends(get_recording_use_cases),
    current_user: dict = Depends(get_recording_view_user),
):
    """Kayit segmenti dosyasini path sizdirmadan ve audit izli olarak dondurur."""
    segment = use_cases.get_segment(segment_id)
    if segment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayit segmenti bulunamadi.")
    path = _safe_recording_file_path(segment)
    write_audit_event(
        "recording.file.access",
        actor=current_user.get("sub"),
        metadata={
            "segment_id": segment.id,
            "camera_id": segment.camera_id,
            "alarm_id": segment.alarm_id,
            "recording_type": segment.recording_type,
            "filename": path.name,
            "file_sha256": segment.file_sha256,
            "size_bytes": segment.size_bytes,
        },
    )
    return FileResponse(
        path=path,
        media_type="video/mp4",
        filename=path.name,
        headers={
            "X-Recording-Segment-Id": str(segment.id or segment_id),
            "X-Recording-SHA256": segment.file_sha256 or "",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{segment_id}/metadata", response_model=RecordingMetadataResponse)
def get_recording_metadata(
    segment_id: int,
    use_cases: RecordingUseCases = Depends(get_recording_use_cases),
    current_user: dict = Depends(get_recording_view_user),
):
    """Playback icin event detection metadata'sini path sizdirmadan dondurur."""
    segment = use_cases.get_segment(segment_id)
    if segment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayit segmenti bulunamadi.")
    return _recording_metadata_response(segment)


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
