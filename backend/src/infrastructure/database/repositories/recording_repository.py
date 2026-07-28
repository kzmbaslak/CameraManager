"""Recording segment SQLAlchemy repository uygulamasi."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy.orm import Session

from src.domain.entities.recording_segment import RecordingSegment
from src.infrastructure.database.models import RecordingSegmentModel


class SqlAlchemyRecordingSegmentRepository:
    """Kayit segmentlerini SQLite uzerinde saklar ve zaman araligina gore listeler."""

    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, model: RecordingSegmentModel) -> RecordingSegment:
        return RecordingSegment(
            id=model.id,
            camera_id=model.camera_id,
            started_at=model.started_at,
            ended_at=model.ended_at,
            recording_type=model.recording_type,
            status=model.status,
            file_path=model.file_path,
            file_sha256=model.file_sha256,
            size_bytes=model.size_bytes,
            codec=model.codec,
            width=model.width,
            height=model.height,
            fps=model.fps,
            alarm_id=model.alarm_id,
            created_at=model.created_at,
        )

    def add(self, segment: RecordingSegment) -> RecordingSegment:
        model = RecordingSegmentModel(
            camera_id=segment.camera_id,
            started_at=segment.started_at,
            ended_at=segment.ended_at,
            recording_type=segment.recording_type,
            status=segment.status,
            file_path=segment.file_path,
            file_sha256=segment.file_sha256,
            size_bytes=segment.size_bytes,
            codec=segment.codec,
            width=segment.width,
            height=segment.height,
            fps=segment.fps,
            alarm_id=segment.alarm_id,
            created_at=segment.created_at,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, segment_id: int) -> RecordingSegment | None:
        if segment_id <= 0:
            return None
        model = self._db.query(RecordingSegmentModel).filter(RecordingSegmentModel.id == segment_id).first()
        return self._to_entity(model) if model else None

    def list_segments(
        self,
        *,
        camera_id: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> Sequence[RecordingSegment]:
        query = self._db.query(RecordingSegmentModel)
        if camera_id is not None:
            query = query.filter(RecordingSegmentModel.camera_id == camera_id)
        if since is not None:
            query = query.filter(RecordingSegmentModel.ended_at.is_(None) | (RecordingSegmentModel.ended_at >= since))
        if until is not None:
            query = query.filter(RecordingSegmentModel.started_at <= until)
        models = (
            query
            .order_by(RecordingSegmentModel.started_at.desc(), RecordingSegmentModel.id.desc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(model) for model in models]

    def list_by_alarm_id(self, alarm_id: int) -> Sequence[RecordingSegment]:
        if alarm_id <= 0:
            return []
        models = (
            self._db.query(RecordingSegmentModel)
            .filter(RecordingSegmentModel.alarm_id == alarm_id)
            .order_by(RecordingSegmentModel.started_at.asc(), RecordingSegmentModel.id.asc())
            .all()
        )
        return [self._to_entity(model) for model in models]

    def list_completed_before(self, cutoff: datetime, limit: int = 1000) -> Sequence[RecordingSegment]:
        models = (
            self._db.query(RecordingSegmentModel)
            .filter(RecordingSegmentModel.ended_at.isnot(None))
            .filter(RecordingSegmentModel.ended_at < cutoff)
            .order_by(RecordingSegmentModel.ended_at.asc(), RecordingSegmentModel.id.asc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(model) for model in models]

    def list_completed_oldest(self, limit: int = 5000) -> Sequence[RecordingSegment]:
        models = (
            self._db.query(RecordingSegmentModel)
            .filter(RecordingSegmentModel.ended_at.isnot(None))
            .order_by(RecordingSegmentModel.ended_at.asc(), RecordingSegmentModel.id.asc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(model) for model in models]

    def delete_by_ids(self, segment_ids: list[int]) -> int:
        safe_ids = [segment_id for segment_id in segment_ids if segment_id > 0]
        if not safe_ids:
            return 0
        count = (
            self._db.query(RecordingSegmentModel)
            .filter(RecordingSegmentModel.id.in_(safe_ids))
            .delete(synchronize_session=False)
        )
        self._db.commit()
        return int(count)
