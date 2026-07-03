from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from src.presentation.api.dependencies import get_alarm_repository, get_current_user, get_operator_user
from src.infrastructure.database.repositories.alarm_repository import SqlAlchemyAlarmRepository
from src.presentation.api.schemas.alarm_schema import AlarmResponse
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

@router.post("/{alarm_id}/acknowledge", response_model=AlarmResponse)
def acknowledge_alarm(
    alarm_id: int,
    repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
    current_user: dict = Depends(get_operator_user),
):
    """Bir alarmın onaylandığını (incelendiğini) işaretler."""
    from datetime import datetime
    alarm = repo.get_by_id(alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm bulunamadı (Alarm not found)")
    
    alarm.acknowledge(datetime.utcnow())
    return repo.update(alarm)
