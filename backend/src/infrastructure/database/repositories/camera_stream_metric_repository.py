"""Kamera stream performans metrikleri SQLAlchemy repository uygulamasi."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy.orm import Session

from src.domain.entities.camera_stream_metric import CameraStreamMetric
from src.infrastructure.database.models import CameraStreamMetricModel


class SqlAlchemyCameraStreamMetricRepository:
    """Stream performans olcumlerini kaydeder ve son gecmisi listeler."""

    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, model: CameraStreamMetricModel) -> CameraStreamMetric:
        return CameraStreamMetric(
            id=model.id,
            camera_id=model.camera_id,
            sampled_at=model.sampled_at,
            producer_running=model.producer_running,
            subscriber_count=model.subscriber_count,
            current_broadcast_fps=model.current_broadcast_fps,
            average_ai_inference_ms=model.average_ai_inference_ms,
            host_cpu_load_percent=model.host_cpu_load_percent,
            host_memory_used_percent=model.host_memory_used_percent,
            reconnects=model.reconnects,
            open_failures=model.open_failures,
            failure_count=model.failure_count,
        )

    def add(self, metric: CameraStreamMetric) -> CameraStreamMetric:
        model = CameraStreamMetricModel(
            camera_id=metric.camera_id,
            sampled_at=metric.sampled_at,
            producer_running=metric.producer_running,
            subscriber_count=metric.subscriber_count,
            current_broadcast_fps=metric.current_broadcast_fps,
            average_ai_inference_ms=metric.average_ai_inference_ms,
            host_cpu_load_percent=metric.host_cpu_load_percent,
            host_memory_used_percent=metric.host_memory_used_percent,
            reconnects=metric.reconnects,
            open_failures=metric.open_failures,
            failure_count=metric.failure_count,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def list_recent(self, camera_id: int, limit: int = 120) -> Sequence[CameraStreamMetric]:
        models = (
            self._db.query(CameraStreamMetricModel)
            .filter(CameraStreamMetricModel.camera_id == camera_id)
            .order_by(CameraStreamMetricModel.sampled_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(model) for model in models]

    def prune_older_than(self, days: int = 7) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = self._db.query(CameraStreamMetricModel).filter(CameraStreamMetricModel.sampled_at < cutoff)
        count = query.count()
        query.delete(synchronize_session=False)
        self._db.commit()
        return count
