import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from typing import List, Optional
from src.presentation.api.dependencies import get_alarm_repository, get_current_user, get_operator_user
from src.infrastructure.database.repositories.alarm_repository import SqlAlchemyAlarmRepository
from src.infrastructure.security.audit_logger import write_audit_event
from src.presentation.api.schemas.alarm_schema import AlarmResolveRequest, AlarmResponse, AlarmUpdate
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


@router.get("/{alarm_id}/snapshot")
def get_alarm_snapshot(
    alarm_id: int,
    request: Request,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_current_user),
):
    """Alarm kanit snapshot dosyasini guvenli dosya siniri icinden dondurur."""
    return _snapshot_file_response(alarm_id, request, repo, current_user, annotated=False)


@router.get("/{alarm_id}/snapshot/annotated")
def get_alarm_annotated_snapshot(
    alarm_id: int,
    request: Request,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_current_user),
):
    """Alarm operator kanit snapshot'ini, varsa insan kutulariyla dondurur."""
    return _snapshot_file_response(alarm_id, request, repo, current_user, annotated=True)

@router.post("/{alarm_id}/acknowledge", response_model=AlarmResponse)
def acknowledge_alarm(
    alarm_id: int,
    request: Request,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_operator_user),
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
    current_user: dict = Depends(get_operator_user),
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
    current_user: dict = Depends(get_operator_user),
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
    current_user: dict = Depends(get_operator_user),
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
