from typing import Optional, Sequence
from sqlalchemy.orm import Session
from src.domain.entities.alarm import Alarm, AlarmSeverity, AlarmStatus, AlarmType, BoundingBox
from src.domain.interfaces.alarm_repository import IAlarmRepository
from src.infrastructure.database.models import AlarmModel

class SqlAlchemyAlarmRepository(IAlarmRepository):
    def __init__(self, db: Session):
        self._db = db

    def _severity_to_entity(self, value) -> AlarmSeverity:
        """DB'deki string/enum severity degerini domain enum'a guvenli cevirir."""
        if isinstance(value, AlarmSeverity):
            return value
        try:
            return AlarmSeverity(value or AlarmSeverity.MEDIUM.value)
        except ValueError:
            return AlarmSeverity.MEDIUM

    def _to_entity(self, model: AlarmModel) -> Alarm:
        bbox = None
        if model.bbox_x is not None and model.bbox_y is not None and model.bbox_width is not None and model.bbox_height is not None:
            bbox = BoundingBox(x=model.bbox_x, y=model.bbox_y, width=model.bbox_width, height=model.bbox_height)
            
        return Alarm(
            id=model.id,
            camera_id=model.camera_id,
            alarm_type=model.alarm_type,
            status=model.status,
            confidence=model.confidence,
            bounding_box=bbox,
            snapshot_path=model.snapshot_path,
            message=model.message,
            severity=self._severity_to_entity(model.severity),
            false_positive=bool(model.false_positive),
            assigned_to=model.assigned_to,
            operator_note=model.operator_note,
            resolution_reason=model.resolution_reason,
            created_at=model.created_at,
            acknowledged_at=model.acknowledged_at,
            resolved_at=model.resolved_at
        )

    def _to_model(self, entity: Alarm) -> AlarmModel:
        model = AlarmModel(
            id=entity.id,
            camera_id=entity.camera_id,
            alarm_type=entity.alarm_type,
            status=entity.status,
            confidence=entity.confidence,
            snapshot_path=entity.snapshot_path,
            message=entity.message,
            severity=entity.severity.value,
            false_positive=entity.false_positive,
            assigned_to=entity.assigned_to,
            operator_note=entity.operator_note,
            resolution_reason=entity.resolution_reason,
            created_at=entity.created_at,
            acknowledged_at=entity.acknowledged_at,
            resolved_at=entity.resolved_at
        )
        if entity.bounding_box:
            model.bbox_x = entity.bounding_box.x
            model.bbox_y = entity.bounding_box.y
            model.bbox_width = entity.bounding_box.width
            model.bbox_height = entity.bounding_box.height
        return model

    def add(self, alarm: Alarm) -> Alarm:
        model = self._to_model(alarm)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, alarm_id: int) -> Alarm | None:
        model = self._db.query(AlarmModel).filter(AlarmModel.id == alarm_id).first()
        if model:
            return self._to_entity(model)
        return None

    def list_by_camera(self, camera_id: int, limit: int = 100) -> Sequence[Alarm]:
        models = self._db.query(AlarmModel).filter(AlarmModel.camera_id == camera_id).order_by(AlarmModel.created_at.desc()).limit(limit).all()
        return [self._to_entity(m) for m in models]

    def list_by_status(self, status: AlarmStatus, limit: int = 100) -> Sequence[Alarm]:
        models = self._db.query(AlarmModel).filter(AlarmModel.status == status).order_by(AlarmModel.created_at.desc()).limit(limit).all()
        return [self._to_entity(m) for m in models]

    def list_all(
        self,
        camera_id: Optional[int] = None,
        alarm_type: Optional[AlarmType] = None,
        status: Optional[AlarmStatus] = None,
        limit: int = 200,
    ) -> Sequence[Alarm]:
        """Tüm alarmları opsiyonel filtrelerle listeler — kamera, tip, durum."""
        q = self._db.query(AlarmModel)
        if camera_id is not None:
            q = q.filter(AlarmModel.camera_id == camera_id)
        if alarm_type is not None:
            q = q.filter(AlarmModel.alarm_type == alarm_type)
        if status is not None:
            q = q.filter(AlarmModel.status == status)
        models = q.order_by(AlarmModel.created_at.desc()).limit(limit).all()
        return [self._to_entity(m) for m in models]

    def update(self, alarm: Alarm) -> Alarm:
        model = self._db.query(AlarmModel).filter(AlarmModel.id == alarm.id).first()
        if model:
            model.status = alarm.status
            model.confidence = alarm.confidence
            model.snapshot_path = alarm.snapshot_path
            model.message = alarm.message
            model.severity = alarm.severity.value
            model.false_positive = alarm.false_positive
            model.assigned_to = alarm.assigned_to
            model.operator_note = alarm.operator_note
            model.resolution_reason = alarm.resolution_reason
            model.acknowledged_at = alarm.acknowledged_at
            model.resolved_at = alarm.resolved_at
            if alarm.bounding_box:
                model.bbox_x = alarm.bounding_box.x
                model.bbox_y = alarm.bounding_box.y
                model.bbox_width = alarm.bounding_box.width
                model.bbox_height = alarm.bounding_box.height
            self._db.commit()
            self._db.refresh(model)
            return self._to_entity(model)
        raise ValueError(f"Alarm with id {alarm.id} not found")
