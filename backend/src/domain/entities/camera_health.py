"""Kamera saglik gecmisi domain entity'si."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CameraHealthSample:
    """Bir kamera icin tek saglik olcumunu temsil eder."""

    id: Optional[int]
    camera_id: int
    checked_at: datetime
    reachable: bool
    status: str
    latency_ms: Optional[float] = None
    failure_reason: Optional[str] = None
