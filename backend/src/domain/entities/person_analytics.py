"""Kamera bazli insan yogunlugu analitigi entity'leri."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CameraPersonHourlyStat:
    """Bir kamera icin tek saatlik insan tespiti ozetini temsil eder."""

    id: Optional[int]
    camera_id: int
    hour_start: datetime
    detection_samples: int
    total_person_count: int
    max_person_count: int
    max_confidence: Optional[float]
    first_detected_at: datetime
    last_detected_at: datetime
