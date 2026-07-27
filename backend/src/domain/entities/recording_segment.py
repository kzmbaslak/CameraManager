"""Kamera video kayit segmenti domain entity'si."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RecordingSegment:
    """Tek kamera icin bir video kayit dosyasi araligini temsil eder."""

    id: Optional[int]
    camera_id: int
    started_at: datetime
    ended_at: Optional[datetime]
    recording_type: str
    status: str
    file_path: str
    file_sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    alarm_id: Optional[int] = None
    created_at: Optional[datetime] = None
