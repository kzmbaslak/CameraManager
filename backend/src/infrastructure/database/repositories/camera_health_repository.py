"""Kamera saglik gecmisi SQLAlchemy repository uygulamasi."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy.orm import Session

from src.domain.entities.camera_health import CameraHealthSample
from src.infrastructure.database.models import CameraHealthSampleModel


class SqlAlchemyCameraHealthRepository:
    """Kamera saglik olcumlerini kaydeder ve son gecmisi listeler."""

    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, model: CameraHealthSampleModel) -> CameraHealthSample:
        return CameraHealthSample(
            id=model.id,
            camera_id=model.camera_id,
            checked_at=model.checked_at,
            reachable=model.reachable,
            status=model.status,
            latency_ms=model.latency_ms,
            failure_reason=model.failure_reason,
        )

    def add(self, sample: CameraHealthSample) -> CameraHealthSample:
        model = CameraHealthSampleModel(
            camera_id=sample.camera_id,
            checked_at=sample.checked_at,
            reachable=sample.reachable,
            status=sample.status,
            latency_ms=sample.latency_ms,
            failure_reason=sample.failure_reason,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def list_recent(self, camera_id: int, limit: int = 120) -> Sequence[CameraHealthSample]:
        models = (
            self._db.query(CameraHealthSampleModel)
            .filter(CameraHealthSampleModel.camera_id == camera_id)
            .order_by(CameraHealthSampleModel.checked_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(model) for model in models]

    def prune_older_than(self, days: int = 7) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = self._db.query(CameraHealthSampleModel).filter(CameraHealthSampleModel.checked_at < cutoff)
        count = query.count()
        query.delete(synchronize_session=False)
        self._db.commit()
        return count
