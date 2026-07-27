import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from typing import List, Optional
from src.application.services.alarm_threshold_suggestions import build_threshold_suggestions
from src.presentation.api.dependencies import (
    get_alarm_operate_user,
    get_alarm_repository,
    get_camera_manage_user,
    get_camera_repository,
    get_current_user,
    get_evidence_export_user,
    get_stream_manager,
)
from src.application.services.camera_stream_manager import CameraStreamManager
from src.infrastructure.database.repositories.alarm_repository import SqlAlchemyAlarmRepository
from src.infrastructure.database.repositories.camera_repository import SqlAlchemyCameraRepository
from src.infrastructure.security.audit_logger import write_audit_event
from src.presentation.api.schemas.alarm_schema import (
    AlarmResolveRequest,
    AlarmResponse,
    AlarmThresholdSuggestionApplyItem,
    AlarmThresholdSuggestionApplyRequest,
    AlarmThresholdSuggestionApplyResponse,
    AlarmThresholdSuggestionItem,
    AlarmTrainingFeedbackItem,
    AlarmUpdate,
)
from src.domain.entities.alarm import AlarmStatus, AlarmType

router = APIRouter(prefix="/alarms", tags=["Alarms"])


def _snapshot_file_response(
    alarm_id: int,
    request: Request,
    repo: SqlAlchemyAlarmRepository,
    current_user: dict,
    annotated: bool = False,
) -> FileResponse:
    """Alarm snapshot varyantini guvenli dosya siniri icinden dondurur."""
    alarm = repo.get_by_id(alarm_id)
    snapshot_path = alarm.snapshot_path if alarm else None
    stored_hash = alarm.snapshot_sha256 if alarm else None
    variant = "raw"
    if alarm and annotated and alarm.snapshot_annotated_path:
        snapshot_path = alarm.snapshot_annotated_path
        stored_hash = alarm.snapshot_annotated_sha256
        variant = "annotated"
    elif annotated:
        variant = "annotated_fallback"
    if not alarm or not snapshot_path:
        raise HTTPException(status_code=404, detail="Alarm snapshot bulunamadi.")

    base_dir = os.path.abspath("snapshots")
    absolute_path = os.path.abspath(snapshot_path)
    if os.path.commonpath([base_dir, absolute_path]) != base_dir:
        raise HTTPException(status_code=403, detail="Snapshot yolu guvenli dizin disinda.")
    if not os.path.isfile(absolute_path):
        raise HTTPException(status_code=404, detail="Snapshot dosyasi bulunamadi.")
    with open(absolute_path, "rb") as file:
        snapshot_sha256 = hashlib.sha256(file.read()).hexdigest()
    if stored_hash != snapshot_sha256:
        if variant == "annotated":
            alarm.snapshot_annotated_sha256 = snapshot_sha256
        else:
            alarm.snapshot_sha256 = snapshot_sha256
        repo.update(alarm)
    write_audit_event(
        "alarm.snapshot.access",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={
            "alarm_id": alarm_id,
            "camera_id": alarm.camera_id,
            "snapshot_sha256": snapshot_sha256,
            "variant": variant,
        },
    )
    return FileResponse(
        absolute_path,
        media_type="image/jpeg",
        headers={"X-Snapshot-SHA256": snapshot_sha256, "X-Snapshot-Variant": variant},
    )


def _build_threshold_suggestions(
    repo: SqlAlchemyAlarmRepository,
    limit: int = 1000,
    minimum_samples: int = 3,
) -> list[AlarmThresholdSuggestionItem]:
    """Alarm repository verisini application servisinin HTTP sozlesmesine map eder."""
    safe_limit = max(1, min(limit, 5000))
    safe_minimum_samples = max(1, min(minimum_samples, 50))
    alarms = repo.list_all(alarm_type=AlarmType.HUMAN_DETECTED, limit=safe_limit)
    return [
        AlarmThresholdSuggestionItem(
            camera_id=suggestion.camera_id,
            sample_count=suggestion.sample_count,
            false_positive_count=suggestion.false_positive_count,
            false_positive_rate=suggestion.false_positive_rate,
            average_confidence=suggestion.average_confidence,
            suggested_confidence_threshold=suggestion.suggested_confidence_threshold,
            recommendation=suggestion.recommendation,
        )
        for suggestion in build_threshold_suggestions(alarms, safe_minimum_samples)
    ]


@router.get("/", response_model=List[AlarmResponse])
def list_alarms(
    camera_id: Optional[int] = None,
    alarm_type: Optional[AlarmType] = None,
    status: Optional[AlarmStatus] = None,
    limit: int = 200,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_current_user),
):
    """Alarmları listeler — kamera, tip ve durum filtreleri opsiyoneldir."""
    return repo.list_all(camera_id=camera_id, alarm_type=alarm_type, status=status, limit=limit)


@router.get("/camera/{camera_id}", response_model=List[AlarmResponse])
def list_camera_alarms(
    camera_id: int,
    limit: int = 100,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_current_user),
):
    """Belirli bir kameraya ait son alarmları (Alarms) listeler."""
    return repo.list_by_camera(camera_id, limit)

@router.get("/status/{status}", response_model=List[AlarmResponse])
def list_alarms_by_status(
    status: AlarmStatus,
    limit: int = 100,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_current_user),
):
    """Belirli bir duruma (örn: NEW, ACKNOWLEDGED) sahip alarmları listeler."""
    return repo.list_by_status(status, limit)


@router.get("/training-feedback", response_model=List[AlarmTrainingFeedbackItem])
def export_training_feedback(
    request: Request,
    limit: int = 500,
    false_positive_only: bool = True,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_evidence_export_user),
):
    """AI threshold/model iyilestirmesi icin sinirli alarm geri bildirimi dondurur."""
    safe_limit = max(1, min(limit, 5000))
    alarms = repo.list_all(alarm_type=AlarmType.HUMAN_DETECTED, limit=safe_limit)
    if false_positive_only:
        alarms = [alarm for alarm in alarms if alarm.false_positive]
    items = [
        AlarmTrainingFeedbackItem(
            alarm_id=alarm.id,
            camera_id=alarm.camera_id,
            created_at=alarm.created_at,
            confidence=alarm.confidence,
            bounding_box=alarm.bounding_box,
            false_positive=alarm.false_positive,
            severity=alarm.severity,
            operator_note=alarm.operator_note,
            resolution_reason=alarm.resolution_reason,
            snapshot_sha256=alarm.snapshot_sha256,
            snapshot_annotated_sha256=alarm.snapshot_annotated_sha256,
        )
        for alarm in alarms
    ]
    write_audit_event(
        "alarm.training_feedback.export",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={
            "count": len(items),
            "limit": safe_limit,
            "false_positive_only": false_positive_only,
        },
    )
    return items


@router.get("/threshold-suggestions", response_model=List[AlarmThresholdSuggestionItem])
def get_threshold_suggestions(
    request: Request,
    limit: int = 1000,
    minimum_samples: int = 3,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_evidence_export_user),
):
    """Yanlis alarm geri bildirimlerinden kamera bazli confidence esigi onerir."""
    safe_limit = max(1, min(limit, 5000))
    safe_minimum_samples = max(1, min(minimum_samples, 50))
    suggestions = _build_threshold_suggestions(repo, safe_limit, safe_minimum_samples)
    write_audit_event(
        "alarm.threshold_suggestions.view",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={
            "count": len(suggestions),
            "limit": safe_limit,
            "minimum_samples": safe_minimum_samples,
        },
    )
    return suggestions


@router.post("/threshold-suggestions/apply", response_model=AlarmThresholdSuggestionApplyResponse)
async def apply_threshold_suggestions(
    data: AlarmThresholdSuggestionApplyRequest,
    request: Request,
    alarm_repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    camera_repo: SqlAlchemyCameraRepository = Depends(get_camera_repository),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_camera_manage_user),
):
    """Secili kamera onerilerini confidence esigi olarak uygular."""
    selected_ids = set(data.camera_ids or [])
    suggestions = _build_threshold_suggestions(alarm_repo, data.limit, data.minimum_samples)
    applicable = [
        suggestion
        for suggestion in suggestions
        if suggestion.suggested_confidence_threshold is not None
        and (not selected_ids or suggestion.camera_id in selected_ids)
    ]

    applied_items: list[AlarmThresholdSuggestionApplyItem] = []
    skipped_count = len(suggestions) - len(applicable)
    for suggestion in applicable:
        camera = camera_repo.get_by_id(suggestion.camera_id)
        if not camera:
            skipped_count += 1
            continue
        previous_threshold = camera.ai_confidence_threshold
        next_threshold = suggestion.suggested_confidence_threshold
        if next_threshold is None or abs(previous_threshold - next_threshold) < 0.001:
            skipped_count += 1
            continue

        camera.ai_confidence_threshold = next_threshold
        camera_repo.update(camera)
        await sm.ensure_running_state(camera.id)
        applied_items.append(
            AlarmThresholdSuggestionApplyItem(
                camera_id=camera.id,
                previous_confidence_threshold=round(previous_threshold, 3),
                applied_confidence_threshold=round(next_threshold, 3),
                sample_count=suggestion.sample_count,
                false_positive_rate=suggestion.false_positive_rate,
            )
        )

    write_audit_event(
        "alarm.threshold_suggestions.apply",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={
            "applied_count": len(applied_items),
            "skipped_count": skipped_count,
            "camera_ids": [item.camera_id for item in applied_items],
        },
    )
    return AlarmThresholdSuggestionApplyResponse(
        applied_count=len(applied_items),
        skipped_count=skipped_count,
        items=applied_items,
    )


@router.get("/{alarm_id}/snapshot")
def get_alarm_snapshot(
    alarm_id: int,
    request: Request,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_evidence_export_user),
):
    """Alarm kanit snapshot dosyasini guvenli dosya siniri icinden dondurur."""
    return _snapshot_file_response(alarm_id, request, repo, current_user, annotated=False)


@router.get("/{alarm_id}/snapshot/annotated")
def get_alarm_annotated_snapshot(
    alarm_id: int,
    request: Request,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_evidence_export_user),
):
    """Alarm operator kanit snapshot'ini, varsa insan kutulariyla dondurur."""
    return _snapshot_file_response(alarm_id, request, repo, current_user, annotated=True)

@router.post("/{alarm_id}/acknowledge", response_model=AlarmResponse)
def acknowledge_alarm(
    alarm_id: int,
    request: Request,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_alarm_operate_user),
):
    """Bir alarmın onaylandığını (incelendiğini) işaretler."""
    from datetime import datetime
    alarm = repo.get_by_id(alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm bulunamadı (Alarm not found)")
    
    alarm.acknowledge(datetime.utcnow())
    updated = repo.update(alarm)
    write_audit_event(
        "alarm.acknowledge",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"alarm_id": alarm_id, "camera_id": alarm.camera_id},
    )
    return updated


@router.patch("/{alarm_id}", response_model=AlarmResponse)
def update_alarm(
    alarm_id: int,
    data: AlarmUpdate,
    request: Request,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_alarm_operate_user),
):
    """Alarm atama ve operator notu alanlarini gunceller."""
    alarm = repo.get_by_id(alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm bulunamadi.")
    fields = data.model_fields_set
    if "assigned_to" in fields:
        alarm.assigned_to = data.assigned_to
    if "operator_note" in fields:
        alarm.operator_note = data.operator_note
    if "severity" in fields and data.severity is not None:
        alarm.severity = data.severity
    if "false_positive" in fields and data.false_positive is not None:
        alarm.false_positive = data.false_positive
    updated = repo.update(alarm)
    write_audit_event(
        "alarm.update",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={
            "alarm_id": alarm_id,
            "camera_id": alarm.camera_id,
            "changed_fields": sorted(fields),
            "assigned_to": alarm.assigned_to,
            "severity": alarm.severity.value,
            "false_positive": alarm.false_positive,
        },
    )
    return updated


@router.post("/{alarm_id}/resolve", response_model=AlarmResponse)
def resolve_alarm(
    alarm_id: int,
    data: AlarmResolveRequest,
    request: Request,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_alarm_operate_user),
):
    """Alarmi cozum nedeniyle kapatir."""
    from datetime import datetime

    alarm = repo.get_by_id(alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm bulunamadi.")
    alarm.resolution_reason = data.resolution_reason
    alarm.false_positive = data.false_positive
    alarm.resolve(datetime.utcnow())
    updated = repo.update(alarm)
    write_audit_event(
        "alarm.resolve",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={
            "alarm_id": alarm_id,
            "camera_id": alarm.camera_id,
            "resolution_reason": data.resolution_reason,
            "false_positive": data.false_positive,
        },
    )
    return updated


@router.post("/{alarm_id}/false-positive", response_model=AlarmResponse)
def mark_alarm_false_positive(
    alarm_id: int,
    request: Request,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_alarm_operate_user),
):
    """Alarmi tek aksiyonla yanlis alarm olarak kapatir."""
    from datetime import datetime

    alarm = repo.get_by_id(alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm bulunamadi.")
    alarm.false_positive = True
    alarm.resolution_reason = alarm.resolution_reason or "Yanlis alarm"
    alarm.resolve(datetime.utcnow())
    updated = repo.update(alarm)
    write_audit_event(
        "alarm.false_positive",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"alarm_id": alarm_id, "camera_id": alarm.camera_id},
    )
    return updated
