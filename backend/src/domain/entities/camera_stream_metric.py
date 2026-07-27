"""Kamera stream performans gecmisi domain entity'si."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CameraStreamMetric:
    """Bir kamera icin tek stream performans olcumunu temsil eder."""

    id: Optional[int]
    camera_id: int
    sampled_at: datetime
    producer_running: bool
    subscriber_count: int
    current_broadcast_fps: Optional[float] = None
    average_ai_inference_ms: Optional[float] = None
    host_cpu_load_percent: Optional[float] = None
    host_memory_used_percent: Optional[float] = None
    reconnects: int = 0
    open_failures: int = 0
    failure_count: int = 0
