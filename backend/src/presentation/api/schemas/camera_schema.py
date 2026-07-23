"""Kamera API istek/yanit semalari ve guvenli alan validasyonlari."""

import json
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.domain.entities.camera import CameraStatus
from src.presentation.api.security_validators import validate_host, validate_port, validate_scan_target


def _validate_ai_time_value(value: Optional[str]) -> Optional[str]:
    """AI aktif saat degerini HH:MM formatinda dogrular."""
    if value is None or value == "":
        return None
    if not re.fullmatch(r"[0-2]\d:[0-5]\d", value):
        raise ValueError("Saat HH:MM formatinda olmalidir.")
    hour = int(value.split(":")[0])
    if hour > 23:
        raise ValueError("Saat 00:00 ile 23:59 arasinda olmalidir.")
    return value


def _validate_roi_polygon_value(value: Optional[str]) -> Optional[str]:
    """Normalize 0-1 araliginda 3-8 noktali ROI poligon JSON'unu dogrular."""
    if value is None or value.strip() == "":
        return None
    points = json.loads(value)
    if not isinstance(points, list) or (len(points) != 0 and not 3 <= len(points) <= 8):
        raise ValueError("ROI poligonu 3-8 nokta iceren JSON liste olmalidir.")
    for point in points:
        if not isinstance(point, dict) or "x" not in point or "y" not in point:
            raise ValueError("ROI noktalari x/y alanlari icermelidir.")
        x = float(point["x"])
        y = float(point["y"])
        if x < 0 or x > 1 or y < 0 or y > 1:
            raise ValueError("ROI koordinatlari 0-1 araliginda normalize olmalidir.")
    return json.dumps(points, separators=(",", ":"))


class CameraCreate(BaseModel):
    """Yeni kamera olusturma istegi."""

    name: str = Field(min_length=1, max_length=120)
    host: str = Field(min_length=1, max_length=255)
    rtsp_path: Optional[str] = Field(default=None, max_length=512)
    rtsp_port: Optional[int] = None
    auto_rtsp_ports: bool = False
    onvif_port: Optional[int] = None
    username: Optional[str] = Field(default=None, max_length=128)
    password: Optional[str] = Field(default=None, max_length=256)
    brand: Optional[str] = Field(default=None, max_length=120)
    model: Optional[str] = Field(default=None, max_length=120)
    ai_confidence_threshold: float = Field(default=0.5, ge=0.05, le=0.95)
    ai_iou_threshold: float = Field(default=0.45, ge=0.05, le=0.95)
    ai_alarm_cooldown_seconds: int = Field(default=60, ge=5, le=3600)
    ai_frame_stride: int = Field(default=1, ge=1, le=30)
    ai_inference_width: int = Field(default=640, ge=320, le=1280)
    ai_active_start: Optional[str] = Field(default=None, max_length=5)
    ai_active_end: Optional[str] = Field(default=None, max_length=5)
    ai_roi_polygon: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("host")
    @classmethod
    def _validate_host(cls, value: str) -> str:
        return validate_host(value)

    @field_validator("rtsp_port")
    @classmethod
    def _validate_rtsp_port(cls, value: Optional[int]) -> Optional[int]:
        return validate_port(value, 554) if value is not None else value

    @field_validator("onvif_port")
    @classmethod
    def _validate_onvif_port(cls, value: Optional[int]) -> Optional[int]:
        return validate_port(value, 80) if value is not None else value

    @field_validator("ai_active_start", "ai_active_end")
    @classmethod
    def _validate_ai_time(cls, value: Optional[str]) -> Optional[str]:
        return _validate_ai_time_value(value)

    @field_validator("ai_roi_polygon")
    @classmethod
    def _validate_ai_roi_polygon(cls, value: Optional[str]) -> Optional[str]:
        return _validate_roi_polygon_value(value)


class CameraUpdate(BaseModel):
    """Kamera alanlarini kismi olarak gunceller; None alanlar degistirilmez."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    host: Optional[str] = Field(default=None, max_length=255)
    rtsp_path: Optional[str] = Field(default=None, max_length=512)
    rtsp_port: Optional[int] = None
    onvif_port: Optional[int] = None
    username: Optional[str] = Field(default=None, max_length=128)
    password: Optional[str] = Field(default=None, max_length=256)
    ai_confidence_threshold: Optional[float] = Field(default=None, ge=0.05, le=0.95)
    ai_iou_threshold: Optional[float] = Field(default=None, ge=0.05, le=0.95)
    ai_alarm_cooldown_seconds: Optional[int] = Field(default=None, ge=5, le=3600)
    ai_frame_stride: Optional[int] = Field(default=None, ge=1, le=30)
    ai_inference_width: Optional[int] = Field(default=None, ge=320, le=1280)
    ai_active_start: Optional[str] = Field(default=None, max_length=5)
    ai_active_end: Optional[str] = Field(default=None, max_length=5)
    ai_roi_polygon: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("host")
    @classmethod
    def _validate_host(cls, value: Optional[str]) -> Optional[str]:
        return validate_host(value) if value is not None else value

    @field_validator("rtsp_port")
    @classmethod
    def _validate_rtsp_port(cls, value: Optional[int]) -> Optional[int]:
        return validate_port(value, 554) if value is not None else value

    @field_validator("onvif_port")
    @classmethod
    def _validate_onvif_port(cls, value: Optional[int]) -> Optional[int]:
        return validate_port(value, 80) if value is not None else value

    @field_validator("ai_active_start", "ai_active_end")
    @classmethod
    def _validate_ai_time(cls, value: Optional[str]) -> Optional[str]:
        return _validate_ai_time_value(value)

    @field_validator("ai_roi_polygon")
    @classmethod
    def _validate_ai_roi_polygon(cls, value: Optional[str]) -> Optional[str]:
        return _validate_roi_polygon_value(value)


class CameraResponse(BaseModel):
    """Kamera yaniti."""

    id: int
    name: str
    host: str
    rtsp_port: int
    onvif_port: int
    username: Optional[str] = None
    rtsp_path: str
    status: CameraStatus
    motion_detection_enabled: bool
    ai_detection_enabled: bool
    ai_confidence_threshold: float
    ai_iou_threshold: float
    ai_alarm_cooldown_seconds: int
    ai_frame_stride: int
    ai_inference_width: int
    ai_active_start: Optional[str] = None
    ai_active_end: Optional[str] = None
    ai_roi_polygon: Optional[str] = None
    created_at: Optional[datetime] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    nvr_id: Optional[int] = None

    class Config:
        from_attributes = True


class CameraScanRequest(BaseModel):
    """Kamera tarama istegi."""

    ip_range: str = Field(min_length=1, max_length=64)
    rtsp_port: Optional[int] = 554
    auto_rtsp_ports: bool = False
    username: Optional[str] = Field(default=None, max_length=128)
    password: Optional[str] = Field(default=None, max_length=256)

    @field_validator("ip_range")
    @classmethod
    def _validate_ip_range(cls, value: str) -> str:
        return validate_scan_target(value)

    @field_validator("rtsp_port")
    @classmethod
    def _validate_rtsp_port(cls, value: Optional[int]) -> Optional[int]:
        return validate_port(value, 554) if value is not None else value


class CameraRtspPreviewRequest(BaseModel):
    """Kaydetmeden RTSP baglanti onizleme testi istegi."""

    camera_id: Optional[int] = None
    name: Optional[str] = Field(default=None, max_length=120)
    host: Optional[str] = Field(default=None, max_length=255)
    rtsp_port: Optional[int] = 554
    rtsp_path: Optional[str] = Field(default=None, max_length=512)
    username: Optional[str] = Field(default=None, max_length=128)
    password: Optional[str] = Field(default=None, max_length=256)

    @field_validator("host")
    @classmethod
    def _validate_host(cls, value: Optional[str]) -> Optional[str]:
        return validate_host(value) if value else value

    @field_validator("rtsp_port")
    @classmethod
    def _validate_rtsp_port(cls, value: Optional[int]) -> Optional[int]:
        return validate_port(value, 554) if value is not None else value


class CameraScanResult(BaseModel):
    """Kamera tarama sonucu."""

    ip: str
    port: int
    path: str
    brand: str
    desc: str
    url: str


class CameraRtspDiagnostics(BaseModel):
    """RTSP baglanti testi sonucu."""

    camera_id: int
    name: str
    host: str
    rtsp_port: int
    rtsp_path: str
    nvr_id: Optional[int] = None
    has_username: bool
    public_url: str
    authenticated_url_masked: str
    tcp_open: bool
    describe_ok: bool
    frame_ok: bool
    authenticated_frame_ok: bool
    anonymous_frame_ok: bool
    message: str


class CameraStreamDiagnostics(BaseModel):
    """Canli akis uretici ve RTSP saglik metrikleri."""

    camera_id: int
    producer_running: bool
    subscriber_count: int
    active_profile: str
    ai_task_running: bool
    ai_provider: Optional[str] = None
    ai_frame_stride: int
    ai_inference_width: int
    cached_frame_available: bool
    last_broadcast_age_seconds: Optional[float] = None
    last_frame_age_seconds: Optional[float] = None
    open_attempts: int
    open_failures: int
    failure_count: int
    retry_cooldown_seconds: float
    warmup_reads: int
    open_timeout_ms: int
    read_timeout_ms: int
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    last_broadcast_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CameraHealthSampleResponse(BaseModel):
    """Tek kamera saglik gecmisi olcumu."""

    id: int
    camera_id: int
    checked_at: datetime
    reachable: bool
    status: str
    latency_ms: Optional[float] = None
    failure_reason: Optional[str] = None

    class Config:
        from_attributes = True


class CameraHealthSummaryResponse(BaseModel):
    """Kamera saglik gecmisi ozet ve trend yaniti."""

    camera_id: int
    sample_count: int
    reachable_count: int
    unreachable_count: int
    availability_percent: Optional[float] = None
    latest_checked_at: Optional[datetime] = None
    latest_latency_ms: Optional[float] = None
    latest_failure_reason: Optional[str] = None
    samples: list[CameraHealthSampleResponse]
