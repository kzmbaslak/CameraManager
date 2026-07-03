from __future__ import annotations

import logging
from typing import Sequence
from urllib.parse import unquote, urlparse

from src.domain.interfaces.camera_probe_service import (
    ICameraProbeService,
    CameraProbeResult,
    DeviceInfo,
)

logger = logging.getLogger(__name__)


class ONVIFProbeService(ICameraProbeService):
    """
    onvif-zeep kütüphanesi ile ONVIF cihazlarını sorgular.
    WSDL dosyaları venv içinde lokal — internet bağlantısı gerekmez.
    """

    def probe_device(self, host: str, onvif_port: int, username: str, password: str) -> DeviceInfo:
        """GetDeviceInformation çağrısıyla marka, model ve seri no alır."""
        cam = self._connect(host, onvif_port, username, password)
        info = cam.devicemgmt.GetDeviceInformation()
        d = self._to_dict(cam, info)
        return DeviceInfo(
            manufacturer=d.get("Manufacturer", "Bilinmiyor"),
            model=d.get("Model", "Bilinmiyor"),
            serial_number=d.get("SerialNumber", ""),
            firmware_version=d.get("FirmwareVersion", ""),
        )

    def get_stream_uris(
        self, host: str, onvif_port: int, username: str, password: str
    ) -> Sequence[CameraProbeResult]:
        """
        NVR / kameradaki tüm ONVIF profillerini okur ve her biri için
        RTSP URI döner. NVR'larda her profil bir kamera kanalına karşılık gelir.
        """
        cam = self._connect(host, onvif_port, username, password)

        # Cihaz bilgisi
        raw_info = cam.devicemgmt.GetDeviceInformation()
        info = self._to_dict(cam, raw_info)
        manufacturer = info.get("Manufacturer", "Bilinmiyor")
        model = info.get("Model", "Bilinmiyor")
        serial = info.get("SerialNumber", "")
        firmware = info.get("FirmwareVersion", "")

        media = cam.create_media_service()
        raw_profiles = media.GetProfiles()
        profiles_data = self._to_dict(cam, raw_profiles)

        profiles = profiles_data.get("Profiles", [])
        if isinstance(profiles, dict):
            profiles = [profiles]

        results: list[CameraProbeResult] = []
        for profile in profiles:
            token = profile.get("token") or profile.get("@token", "")
            name = profile.get("Name", token)

            try:
                stream_req = media.create_type("GetStreamUri")
                stream_req.StreamSetup = {
                    "Stream": "RTP-Unicast",
                    "Transport": {"Protocol": "RTSP"},
                }
                stream_req.ProfileToken = token
                raw_uri = media.GetStreamUri(stream_req)
                uri_data = self._to_dict(cam, raw_uri)
                rtsp_url = uri_data.get("Uri", "")
            except Exception as exc:
                logger.warning(f"Profil {token} için RTSP URI alınamadı: {exc}")
                rtsp_url = ""

            if rtsp_url:
                results.append(
                    CameraProbeResult(
                        manufacturer=manufacturer,
                        model=model,
                        rtsp_url=rtsp_url,
                        onvif_port=onvif_port,
                        profile_token=token,
                        profile_name=name,
                        serial_number=serial,
                        firmware_version=firmware,
                    )
                )

        return results

    # ------------------------------------------------------------------

    @staticmethod
    def _connect(host: str, port: int, username: str, password: str):
        try:
            from onvif import ONVIFCamera
            from requests import Session
            from requests.auth import HTTPDigestAuth, HTTPBasicAuth
            from zeep.transports import Transport
        except ImportError as e:
            raise RuntimeError("onvif-zeep veya requests kütüphanesi bulunamadı.") from e

        # 1. Standart WS-Security bağlantısı dene
        last_exception = None
        try:
            cam = ONVIFCamera(host=host, port=port, user=username, passwd=password)
            # Gerçekten bağlandığını doğrulamak için hafif bir çağrı yapıyoruz
            cam.devicemgmt.GetDeviceInformation()
            return cam
        except Exception as exc:
            logger.info(f"Standard ONVIF WS-Security failed for {host}:{port}, trying HTTP Digest Auth: {exc}")
            last_exception = exc

        # 2. HTTP Digest Authentication dene (TI IPNC / legacy Illustra cihazları için)
        if username and password:
            try:
                session = Session()
                session.auth = HTTPDigestAuth(username, password)
                transport = Transport(session=session)
                cam = ONVIFCamera(host=host, port=port, user=username, passwd=password, transport=transport)
                cam.devicemgmt.GetDeviceInformation()
                return cam
            except Exception as exc:
                logger.info(f"HTTP Digest Auth failed for {host}:{port}, trying HTTP Basic Auth: {exc}")
                last_exception = exc

            # 3. HTTP Basic Authentication dene
            try:
                session = Session()
                session.auth = HTTPBasicAuth(username, password)
                transport = Transport(session=session)
                cam = ONVIFCamera(host=host, port=port, user=username, passwd=password, transport=transport)
                cam.devicemgmt.GetDeviceInformation()
                return cam
            except Exception as exc:
                logger.info(f"HTTP Basic Auth failed for {host}:{port}: {exc}")
                last_exception = exc

        raise ConnectionError(f"ONVIF bağlantısı kurulamadı ({host}:{port}): {last_exception}")

    @staticmethod
    def _to_dict(cam, obj) -> dict:
        """zeep nesnelerini dict'e çevirir."""
        try:
            if hasattr(cam, "to_dict"):
                return cam.to_dict(obj) or {}
            return dict(obj) if obj else {}
        except Exception:
            return {}

    @staticmethod
    def parse_rtsp_path(rtsp_url: str, host: str) -> tuple[int, str]:
        """
        rtsp://user:pass@host:554/path/here?query → (554, '/path/here?query')
        Kimlik bilgileri ve host çıkarılır; sadece port, path ve query döner.
        """
        try:
            parsed = urlparse(rtsp_url)
            port = parsed.port or 554
            path = parsed.path or ""
            if parsed.query:
                path = f"{path}?{parsed.query}"
            return port, path
        except Exception:
            return 554, ""

    @staticmethod
    def parse_rtsp_endpoint(rtsp_url: str, fallback_host: str) -> dict:
        """
        Tam RTSP URL'sini bağlantı alanlarına ayırır.
        rtsp://user:pass@host:554/path?x=1 → host/port/path/username/password.
        """
        try:
            parsed = urlparse(rtsp_url)
            host = parsed.hostname or fallback_host
            if host in {"0.0.0.0", "127.0.0.1", "localhost"}:
                host = fallback_host
            path = parsed.path or ""
            if parsed.query:
                path = f"{path}?{parsed.query}"
            return {
                "host": host,
                "port": parsed.port or 554,
                "path": path,
                "username": unquote(parsed.username) if parsed.username else None,
                "password": unquote(parsed.password) if parsed.password else None,
            }
        except Exception:
            return {
                "host": fallback_host,
                "port": 554,
                "path": "",
                "username": None,
                "password": None,
            }
