"""
NVR (Network Video Recorder) Pydantic semalari.

Bu moduldeki siniflar, NVR API endpoint'lerinin istek ve yanit veri
yapilarini tanimlar. Parolalar yanitlarda hicbir zaman dondurulmez.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from src.presentation.api.security_validators import validate_host, validate_port, validate_scan_target


class NVRCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    host: str = Field(min_length=1, max_length=255)
    onvif_port: int = 80
    username: Optional[str] = Field(default=None, max_length=128)
    password: Optional[str] = Field(default=None, max_length=256)
    brand: Optional[str] = Field(default=None, max_length=120)
    model: Optional[str] = Field(default=None, max_length=120)

    @field_validator("host")
    @classmethod
    def _validate_host(cls, value: str) -> str:
        return validate_host(value)

    @field_validator("onvif_port")
    @classmethod
    def _validate_onvif_port(cls, value: int) -> int:
        return validate_port(value, 80)


class NVRResponse(BaseModel):
    id: int
    name: str
    host: str
    onvif_port: int
    username: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NVRPageResponse(BaseModel):
    """Sayfali NVR liste yaniti."""

    items: List[NVRResponse]
    total: int
    page: int
    page_size: int


class NVRUpdate(BaseModel):
    """NVR cihazini kismi olarak gunceller. None alanlar degistirilmez."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    host: Optional[str] = Field(default=None, max_length=255)
    onvif_port: Optional[int] = None
    username: Optional[str] = Field(default=None, max_length=128)
    password: Optional[str] = Field(default=None, max_length=256)

    @field_validator("host")
    @classmethod
    def _validate_host(cls, value: Optional[str]) -> Optional[str]:
        return validate_host(value) if value is not None else value

    @field_validator("onvif_port")
    @classmethod
    def _validate_onvif_port(cls, value: Optional[int]) -> Optional[int]:
        return validate_port(value, 80) if value is not None else value


class NVRProbeRequest(BaseModel):
    onvif_port: Optional[int] = None

    @field_validator("onvif_port")
    @classmethod
    def _validate_onvif_port(cls, value: Optional[int]) -> Optional[int]:
        return validate_port(value, 80) if value is not None else value


class NVRChannelInfo(BaseModel):
    profile_token: str = Field(min_length=1, max_length=256)
    profile_name: str = Field(min_length=1, max_length=256)
    manufacturer: Optional[str] = Field(default=None, max_length=120)
    model: Optional[str] = Field(default=None, max_length=120)
    rtsp_url: str = Field(min_length=1, max_length=2048)
    source: str = Field(default="onvif", max_length=32)
    diagnostic: Optional[str] = Field(default=None, max_length=1024)


class NVRProbeDiagnostics(BaseModel):
    source: str
    onvif_ok: bool
    fallback_used: bool
    device_manufacturer: Optional[str] = None
    device_model: Optional[str] = None
    profile_count: int = 0
    stream_uri_count: int = 0
    onvif_error: Optional[str] = None
    fallback_error: Optional[str] = None
    channels: List[NVRChannelInfo] = Field(default_factory=list)


class NVRDiscoverResponse(BaseModel):
    xaddr: str
    host: str
    port: int


class NVRImportRequest(BaseModel):
    channels: List[NVRChannelInfo] = Field(min_length=1, max_length=64)


class NVRScanRequest(BaseModel):
    ip_range: str = Field(min_length=1, max_length=64)
    rtsp_port: Optional[int] = 554
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


class NVRScanResponse(BaseModel):
    host: str
    port: int
    brand: str
    model: str
