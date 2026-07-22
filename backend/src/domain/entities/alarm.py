from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class AlarmStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlarmType(str, Enum):
    HUMAN_DETECTED = "human_detected"
    CAMERA_OFFLINE = "camera_offline"
    MOTION_DETECTED = "motion_detected"


class AlarmSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int


@dataclass
class Alarm:
    id: Optional[int]
    camera_id: int
    alarm_type: AlarmType
    status: AlarmStatus = AlarmStatus.NEW
    confidence: Optional[float] = None
    bounding_box: Optional[BoundingBox] = None
    snapshot_path: Optional[str] = None
    message: Optional[str] = None
    severity: AlarmSeverity = AlarmSeverity.MEDIUM
    false_positive: bool = False
    assigned_to: Optional[str] = None
    operator_note: Optional[str] = None
    resolution_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    def acknowledge(self, acknowledged_at: datetime) -> None:
        self.status = AlarmStatus.ACKNOWLEDGED
        self.acknowledged_at = acknowledged_at

    def resolve(self, resolved_at: datetime) -> None:
        self.status = AlarmStatus.RESOLVED
        self.resolved_at = resolved_at
