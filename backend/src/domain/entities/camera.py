from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class CameraStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class Camera:
    id: Optional[int]
    name: str
    host: str
    rtsp_port: int = 554
    onvif_port: int = 80
    username: Optional[str] = None
    encrypted_password: Optional[str] = None
    rtsp_path: str = ""
    status: CameraStatus = CameraStatus.INACTIVE
    motion_detection_enabled: bool = False
    ai_detection_enabled: bool = False
    ai_confidence_threshold: float = 0.5
    ai_iou_threshold: float = 0.45
    ai_alarm_cooldown_seconds: int = 60
    ai_frame_stride: int = 1
    ai_inference_width: int = 640
    ai_active_start: Optional[str] = None
    ai_active_end: Optional[str] = None
    ai_roi_polygon: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    brand: Optional[str] = None      # ONVIF'ten veya kullanıcıdan gelen marka
    model: Optional[str] = None      # ONVIF'ten veya kullanıcıdan gelen model
    nvr_id: Optional[int] = None     # Bağlı olduğu NVR (None = direkt kamera)

    def activate(self) -> None:
        self.status = CameraStatus.ACTIVE

    def deactivate(self) -> None:
        self.status = CameraStatus.INACTIVE

    def mark_error(self) -> None:
        self.status = CameraStatus.ERROR

    @property
    def is_enabled_for_detection(self) -> bool:
        return self.status in {CameraStatus.ACTIVE, CameraStatus.ERROR} and self.ai_detection_enabled
