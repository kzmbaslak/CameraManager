from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from src.domain.entities.camera import CameraStatus


class CameraCreate(BaseModel):
    name: str
    host: str
    rtsp_path: Optional[str] = None
    rtsp_port: Optional[int] = None
    auto_rtsp_ports: bool = False
    onvif_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None


class CameraUpdate(BaseModel):
    """Kamera alanlarını kısmi olarak günceller. None gönderilen alanlar değiştirilmez."""
    name: Optional[str] = None
    host: Optional[str] = None
    rtsp_path: Optional[str] = None
    rtsp_port: Optional[int] = None
    onvif_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None  # None → şifre değiştirilmez


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
    ip_range: str
    rtsp_port: Optional[int] = 554
    auto_rtsp_ports: bool = False
    username: Optional[str] = None
    password: Optional[str] = None


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
