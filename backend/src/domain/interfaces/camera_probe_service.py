from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence


@dataclass
class CameraProbeResult:
    """ONVIF ile otomatik tespit edilen kamera / NVR kanal bilgileri."""
    manufacturer: str
    model: str
    rtsp_url: str          # Tam URL: rtsp://host:554/path
    onvif_port: int
    profile_token: str
    profile_name: str
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    source: str = "onvif"
    diagnostic: Optional[str] = None


@dataclass
class DeviceInfo:
    """ONVIF GetDeviceInformation sonucu."""
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str


class ICameraProbeService(Protocol):
    def probe_device(self, host: str, onvif_port: int, username: str, password: str) -> DeviceInfo: ...
    def get_stream_uris(self, host: str, onvif_port: int, username: str, password: str) -> Sequence[CameraProbeResult]: ...
