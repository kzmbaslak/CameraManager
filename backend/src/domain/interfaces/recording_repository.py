"""Recording segment repository port'u."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from src.domain.entities.recording_segment import RecordingSegment


class IRecordingSegmentRepository(Protocol):
    """Kayit segmenti kaliciligi icin domain port'u."""

    def add(self, segment: RecordingSegment) -> RecordingSegment:
        ...

    def list_segments(
        self,
        *,
        camera_id: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> Sequence[RecordingSegment]:
        ...

    def list_completed_before(self, cutoff: datetime, limit: int = 1000) -> Sequence[RecordingSegment]:
        ...

    def list_completed_oldest(self, limit: int = 5000) -> Sequence[RecordingSegment]:
        ...

    def delete_by_ids(self, segment_ids: list[int]) -> int:
        ...
