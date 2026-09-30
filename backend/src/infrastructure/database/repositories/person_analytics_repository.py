"""Kamera insan yogunlugu analitigi SQLAlchemy repository uygulamasi."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy.orm import Session

from src.domain.entities.person_analytics import CameraPersonHourlyStat
from src.infrastructure.database.models import CameraPersonHourlyStatModel
from src.infrastructure.time_utils import utc_now


class SqlAlchemyPersonAnalyticsRepository:
    """Saatlik insan tespiti istatistiklerini gunceller ve listeler."""

    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, model: CameraPersonHourlyStatModel) -> CameraPersonHourlyStat:
        return CameraPersonHourlyStat(
            id=model.id,
            camera_id=model.camera_id,
            hour_start=model.hour_start,
            detection_samples=model.detection_samples,
            total_person_count=model.total_person_count,
            max_person_count=model.max_person_count,
            max_confidence=model.max_confidence,
            first_detected_at=model.first_detected_at,
            last_detected_at=model.last_detected_at,
        )

    @staticmethod
    def _hour_start(value: datetime) -> datetime:
        return value.replace(minute=0, second=0, microsecond=0)

    @staticmethod
    def _db_datetime(value: datetime) -> datetime:
        return value.replace(tzinfo=None)

    def record_detection(self, camera_id: int, detected_at: datetime, person_count: int, max_confidence: float | None) -> CameraPersonHourlyStat:
        """Tek AI tespit sonucunu kamera+saat kovasina ekler."""
        if person_count <= 0:
            raise ValueError("person_count pozitif olmalidir")
        detected_at = self._db_datetime(detected_at)
        hour_start = self._hour_start(detected_at)
        model = (
            self._db.query(CameraPersonHourlyStatModel)
            .filter(
                CameraPersonHourlyStatModel.camera_id == camera_id,
                CameraPersonHourlyStatModel.hour_start == hour_start,
            )
            .first()
        )
        if model is None:
            model = CameraPersonHourlyStatModel(
                camera_id=camera_id,
                hour_start=hour_start,
                detection_samples=1,
                total_person_count=person_count,
                max_person_count=person_count,
                max_confidence=max_confidence,
                first_detected_at=detected_at,
                last_detected_at=detected_at,
            )
            self._db.add(model)
        else:
            model.detection_samples = (model.detection_samples or 0) + 1
            model.total_person_count = (model.total_person_count or 0) + person_count
            model.max_person_count = max(model.max_person_count or 0, person_count)
            if max_confidence is not None:
                model.max_confidence = max(model.max_confidence or 0.0, max_confidence)
            model.first_detected_at = min(model.first_detected_at, detected_at)
            model.last_detected_at = max(model.last_detected_at, detected_at)
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def list_hourly(self, camera_id: int, since: datetime, until: datetime, limit: int = 168) -> Sequence[CameraPersonHourlyStat]:
        since = self._db_datetime(since)
        until = self._db_datetime(until)
        models = (
            self._db.query(CameraPersonHourlyStatModel)
            .filter(CameraPersonHourlyStatModel.camera_id == camera_id)
            .filter(CameraPersonHourlyStatModel.hour_start >= since)
            .filter(CameraPersonHourlyStatModel.hour_start <= until)
            .order_by(CameraPersonHourlyStatModel.hour_start.asc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(model) for model in models]

    def prune_older_than(self, days: int = 30) -> int:
        cutoff = self._db_datetime(utc_now() - timedelta(days=days))
        query = self._db.query(CameraPersonHourlyStatModel).filter(CameraPersonHourlyStatModel.hour_start < cutoff)
        count = query.count()
        query.delete(synchronize_session=False)
        self._db.commit()
        return count
