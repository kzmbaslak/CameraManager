from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from src.domain.entities.camera import CameraStatus
from src.presentation.api.security_validators import validate_host, validate_port, validate_scan_target


class CameraCreate(BaseModel):
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


class CameraUpdate(BaseModel):
    """Kamera alanlarını kısmi olarak günceller. None gönderilen alanlar değiştirilmez."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    host: Optional[str] = Field(default=None, max_length=255)
    rtsp_path: Optional[str] = Field(default=None, max_length=512)
    rtsp_port: Optional[int] = None
    onvif_port: Optional[int] = None
    username: Optional[str] = Field(default=None, max_length=128)
    password: Optional[str] = Field(default=None, max_length=256)  # None → şifre değiştirilmez

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


class CameraResponse(BaseModel):
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
    created_at: Optional[datetime] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    nvr_id: Optional[int] = None

    class Config:
        from_attributes = True


class CameraScanRequest(BaseModel):
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


class CameraScanResult(BaseModel):
    ip: str
    port: int
    path: str
    brand: str
    desc: str
    url: str


class CameraRtspDiagnostics(BaseModel):
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
    camera_id: int
    producer_running: bool
    subscriber_count: int
    active_profile: str
    ai_task_running: bool
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
