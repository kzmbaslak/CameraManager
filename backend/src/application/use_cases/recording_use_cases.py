"""Video kayit segmentleri icin uygulama use-case'leri."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from src.domain.entities.recording_segment import RecordingSegment
from src.domain.interfaces.recording_repository import IRecordingSegmentRepository


class RecordingUseCases:
    """Kayit envanteri sorgulama ve segment ekleme is kurallarini yonetir."""

    def __init__(self, recording_repository: IRecordingSegmentRepository):
        self._recording_repository = recording_repository

    def add_segment(self, segment: RecordingSegment) -> RecordingSegment:
        if not segment.file_path:
            raise ValueError("Kayit segmenti dosya yolu gereklidir.")
        if segment.ended_at and segment.ended_at < segment.started_at:
            raise ValueError("Kayit bitis zamani baslangictan once olamaz.")
        return self._recording_repository.add(segment)

    def get_segment(self, segment_id: int) -> RecordingSegment | None:
        if segment_id <= 0:
            return None
        return self._recording_repository.get_by_id(segment_id)

    def list_segments(
        self,
        *,
        camera_id: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> Sequence[RecordingSegment]:
        safe_limit = min(max(limit, 1), 500)
        return self._recording_repository.list_segments(
            camera_id=camera_id,
            since=since,
            until=until,
            limit=safe_limit,
        )
