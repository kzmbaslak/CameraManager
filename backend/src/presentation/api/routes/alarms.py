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
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_current_user),
):
    """Alarm kanit snapshot dosyasini guvenli dosya siniri icinden dondurur."""
    alarm = repo.get_by_id(alarm_id)
    if not alarm or not alarm.snapshot_path:
        raise HTTPException(status_code=404, detail="Alarm snapshot bulunamadi.")

    base_dir = os.path.abspath("snapshots")
    snapshot_path = os.path.abspath(alarm.snapshot_path)
    if os.path.commonpath([base_dir, snapshot_path]) != base_dir:
        raise HTTPException(status_code=403, detail="Snapshot yolu guvenli dizin disinda.")
    if not os.path.isfile(snapshot_path):
        raise HTTPException(status_code=404, detail="Snapshot dosyasi bulunamadi.")
    return FileResponse(snapshot_path, media_type="image/jpeg")

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
    alarm.assigned_to = data.assigned_to
    alarm.operator_note = data.operator_note
    updated = repo.update(alarm)
    write_audit_event(
        "alarm.update",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"alarm_id": alarm_id, "camera_id": alarm.camera_id, "assigned_to": data.assigned_to},
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
    alarm.resolve(datetime.utcnow())
    updated = repo.update(alarm)
    write_audit_event(
        "alarm.resolve",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"alarm_id": alarm_id, "camera_id": alarm.camera_id, "resolution_reason": data.resolution_reason},
    )
    return updated
