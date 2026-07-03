"""
OpenCV tabanlı RTSP akış okuyucu.

Kamera başına tek bir VideoCapture nesnesi tutar.
OPENCV_FFMPEG_CAPTURE_OPTIONS main.py tarafından process başlangıcında
(diğer importlardan önce) set edilir; bu modül o değeri değiştirmez —
thread başına env var döngüsü race condition yarattığı için kaldırıldı.
"""
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime

import cv2
import numpy as np

from src.domain.entities.camera import Camera
from src.domain.interfaces.frame_source import IFrameSource

logger = logging.getLogger(__name__)

# CAP_PROP_OPEN_TIMEOUT_MSEC OpenCV bazı sürümlerde çalışmıyor (30s varsayılan devreye giriyor).
# Bağlantı başarısız olursa bu süre kadar bekle — ghost thread birikimine karşı koruma.
_CONNECT_RETRY_COOLDOWN = 12.0  # saniye


@dataclass(frozen=True)
class _WarmupProfile:
    open_timeout_ms: int
    read_timeout_ms: int
    retry_cooldown_seconds: float
    warmup_reads: int = 1


def _mask_url(url: str) -> str:
    """Loglama için RTSP URL'sindeki şifreyi maskeler."""
    return re.sub(r"rtsp://([^:@]+):[^@]+@", r"rtsp://\1:***@", url)


def _open_cap(
    rtsp_url: str,
    camera_id: int | None = None,
    profile: _WarmupProfile | None = None,
) -> tuple[cv2.VideoCapture, np.ndarray | None]:
    """FFMPEG backend ile VideoCapture açar ve ilk frame'i doğrular.

    Başarılı olursa açık (isOpened=True) ve ilk frame'i okumuş cap döner.
    Tüm denemeler başarısız olursa kapalı (isOpened=False) boş cap döner.

    Transport ve timeout OPENCV_FFMPEG_CAPTURE_OPTIONS env var üzerinden gelir
    (main.py'de process başlangıcında set edilir — thread başına DEĞİŞTİRİLMEZ).
    """
    label = f"Kamera {camera_id}" if camera_id is not None else "Kamera?"
    masked = _mask_url(rtsp_url)
    profile = profile or _WarmupProfile(
        open_timeout_ms=5_000,
        read_timeout_ms=3_000,
        retry_cooldown_seconds=_CONNECT_RETRY_COOLDOWN,
    )
    logger.info(f"[RTSP] {label} bağlantı deneniyor → {masked}")

    cap = cv2.VideoCapture()
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, profile.open_timeout_ms)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, profile.read_timeout_ms)
    cap.open(rtsp_url, cv2.CAP_FFMPEG)

    if cap.isOpened():
        for _ in range(max(1, profile.warmup_reads)):
            ok, frame = cap.read()
            if ok and frame is not None:
                h, w = frame.shape[:2]
                logger.info(f"[RTSP] {label} BAĞLANDI — {w}x{h} @ {masked}")
                return cap, frame
        logger.warning(f"[RTSP] {label} açıldı ama ilk frame okunamadı → {masked}")
        cap.release()
    else:
        logger.warning(f"[RTSP] {label} VideoCapture açılamadı → {masked}")
        cap.release()

    logger.error(f"[RTSP] {label} bağlantı başarısız → {masked}")
    return cv2.VideoCapture(), None


class OpenCVStreamReader(IFrameSource):
    """RTSP akışlarını OpenCV ile okuyan altyapı sınıfı."""

    def __init__(self, password_service=None):
        self._caps: dict[int, cv2.VideoCapture] = {}
        self._caps_urls: dict[int, str] = {}
        self._first_frames: dict[int, np.ndarray] = {}
        self._password_service = password_service
        self._last_fail_time: dict[int, float] = {}  # camera_id → son başarısız bağlantı zamanı
        self._failure_counts: dict[int, int] = {}
        self._telemetry: dict[int, dict] = {}

    def _build_rtsp_urls(self, camera: Camera) -> list[str]:
        from urllib.parse import quote

        # RFC 3986: sub-delimiter karakterler (@ : / ? # hariç) şifrede encode edilmemeli.
        # FFmpeg URL'i parse ederken bu karakterleri decode etmez; örneğin ! → %21
        # encode edilirse Digest hash yanlış hesaplanır → 401.
        _PWD_SAFE = "!$&'()*+,;="

        path = camera.rtsp_path or ""
        if path and not path.startswith("/"):
            path = f"/{path}"

        urls = []
        if camera.username:
            password = ""
            if camera.encrypted_password:
                password = camera.encrypted_password
                if self._password_service:
                    try:
                        password = self._password_service.decrypt(password)
                    except Exception:
                        pass
            auth = f"{quote(camera.username, safe='')}:{quote(password or '', safe=_PWD_SAFE)}@"
            urls.append(f"rtsp://{auth}{camera.host}:{camera.rtsp_port}{path}")

        urls.append(f"rtsp://{camera.host}:{camera.rtsp_port}{path}")
        return list(dict.fromkeys(urls))

    def _select_warmup_profile(self, camera: Camera) -> _WarmupProfile:
        """Cihaz metadatasına göre bağlantı ve retry profilini seçer."""
        brand = (camera.brand or "").lower()
        model = (camera.model or "").lower()
        path = (camera.rtsp_path or "").lower()
        host_hint = f"{brand} {model} {path}"

        if "illustra" in host_hint or "i610" in host_hint or camera.rtsp_port == 7778 or "primarystream" in path:
            return _WarmupProfile(
                open_timeout_ms=3_500,
                read_timeout_ms=2_000,
                retry_cooldown_seconds=5.0,
                warmup_reads=2,
            )

        if camera.nvr_id is not None or "videoedge" in host_hint or "nvr" in host_hint:
            return _WarmupProfile(
                open_timeout_ms=5_500,
                read_timeout_ms=3_000,
                retry_cooldown_seconds=10.0,
                warmup_reads=1,
            )

        return _WarmupProfile(
            open_timeout_ms=5_000,
            read_timeout_ms=3_000,
            retry_cooldown_seconds=_CONNECT_RETRY_COOLDOWN,
            warmup_reads=1,
        )

    def _select_profile_name(self, camera: Camera) -> str:
        """Seçilen warm-up profilinin insan okunur adını döner."""
        brand = (camera.brand or "").lower()
        model = (camera.model or "").lower()
        path = (camera.rtsp_path or "").lower()
        host_hint = f"{brand} {model} {path}"

        if "illustra" in host_hint or "i610" in host_hint or camera.rtsp_port == 7778 or "primarystream" in path:
            return "illustra_fast"
        if camera.nvr_id is not None or "videoedge" in host_hint or "nvr" in host_hint:
            return "videoedge_nvr"
        return "default"

    def _current_retry_cooldown(self, camera_id: int, profile: _WarmupProfile) -> float:
        """Ardışık hata sayısına göre artan cooldown üretir."""
        failures = self._failure_counts.get(camera_id, 0)
        if failures <= 0:
            return profile.retry_cooldown_seconds
        return min(profile.retry_cooldown_seconds * (2 ** (failures - 1)), 30.0)

    def _ensure_telemetry(self, camera_id: int) -> dict:
        telemetry = self._telemetry.get(camera_id)
        if telemetry is None:
            telemetry = {
                "open_attempts": 0,
                "open_failures": 0,
                "last_success_at": None,
                "last_failure_at": None,
                "last_frame_at": None,
                "profile": "default",
            }
            self._telemetry[camera_id] = telemetry
        return telemetry

    def _mark_open_attempt(self, camera_id: int, profile_name: str) -> None:
        telemetry = self._ensure_telemetry(camera_id)
        telemetry["open_attempts"] += 1
        telemetry["profile"] = profile_name

    def _mark_open_failure(self, camera_id: int) -> None:
        telemetry = self._ensure_telemetry(camera_id)
        telemetry["open_failures"] += 1
        telemetry["last_failure_at"] = datetime.utcnow()

    def _mark_success(self, camera_id: int) -> None:
        telemetry = self._ensure_telemetry(camera_id)
        now = datetime.utcnow()
        telemetry["last_success_at"] = now
        telemetry["last_frame_at"] = now

    def read_frame(self, camera: Camera) -> np.ndarray | None:
        """Kameradan bir kare okur; bağlantı kesilmişse yeniden açar."""
        if camera.id is None:
            return None

        profile = self._select_warmup_profile(camera)
        profile_name = self._select_profile_name(camera)
        telemetry = self._ensure_telemetry(camera.id)
        telemetry["profile"] = profile_name
        rtsp_urls = self._build_rtsp_urls(camera)

        # URL değiştiyse eski capture'ı serbest bırak
        if camera.id in self._caps and self._caps_urls.get(camera.id) not in rtsp_urls:
            logger.info(f"[RTSP] Kamera {camera.id} URL değişti — bağlantı yenileniyor")
            self._caps[camera.id].release()
            del self._caps[camera.id]
            self._caps_urls.pop(camera.id, None)
            self._first_frames.pop(camera.id, None)

        # Capture yoksa aç; son başarısız denemeden bu yana cooldown süresi geçmediyse atla
        if camera.id not in self._caps:
            last_fail = self._last_fail_time.get(camera.id, 0)
            if time.monotonic() - last_fail < self._current_retry_cooldown(camera.id, profile):
                return None  # Cooldown: bağlantı henüz yeniden denenmeyecek
            for rtsp_url in rtsp_urls:
                self._mark_open_attempt(camera.id, profile_name)
                cap, first_frame = _open_cap(rtsp_url, camera.id, profile)
                self._caps[camera.id] = cap
                self._caps_urls[camera.id] = rtsp_url
                if cap.isOpened():
                    if first_frame is not None:
                        self._first_frames[camera.id] = first_frame
                        self._mark_success(camera.id)
                    self._last_fail_time.pop(camera.id, None)  # başarılı, cooldown sıfırla
                    self._failure_counts.pop(camera.id, None)
                    break
                cap.release()
                self._mark_open_failure(camera.id)
            if not self._caps.get(camera.id, cv2.VideoCapture()).isOpened():
                self._last_fail_time[camera.id] = time.monotonic()
                self._failure_counts[camera.id] = self._failure_counts.get(camera.id, 0) + 1

        cap = self._caps[camera.id]
        if not cap.isOpened():
            last_fail = self._last_fail_time.get(camera.id, 0)
            if time.monotonic() - last_fail < self._current_retry_cooldown(camera.id, profile):
                self._caps.pop(camera.id, None)
                self._caps_urls.pop(camera.id, None)
                self._first_frames.pop(camera.id, None)
                return None  # Cooldown
            logger.warning(f"[RTSP] Kamera {camera.id} capture kapalı — yeniden açılıyor")
            cap.release()
            for rtsp_url in rtsp_urls:
                self._mark_open_attempt(camera.id, profile_name)
                cap, first_frame = _open_cap(rtsp_url, camera.id, profile)
                self._caps[camera.id] = cap
                self._caps_urls[camera.id] = rtsp_url
                if cap.isOpened():
                    if first_frame is not None:
                        self._first_frames[camera.id] = first_frame
                        self._mark_success(camera.id)
                    self._last_fail_time.pop(camera.id, None)
                    self._failure_counts.pop(camera.id, None)
                    break
                cap.release()
                self._mark_open_failure(camera.id)
            if not self._caps[camera.id].isOpened():
                logger.error(f"[RTSP] Kamera {camera.id} yeniden açma başarısız")
                self._caps.pop(camera.id, None)
                self._caps_urls.pop(camera.id, None)
                self._first_frames.pop(camera.id, None)
                self._last_fail_time[camera.id] = time.monotonic()
                self._failure_counts[camera.id] = self._failure_counts.get(camera.id, 0) + 1
                return None
            cap = self._caps[camera.id]

        cached_frame = self._first_frames.pop(camera.id, None)
        if cached_frame is not None:
            self._mark_success(camera.id)
            return cached_frame

        ret, frame = cap.read()
        if not ret:
            logger.warning(f"[RTSP] Kamera {camera.id} frame read başarısız — bağlantı yenileniyor")
            cap.release()
            self._caps.pop(camera.id, None)
            self._caps_urls.pop(camera.id, None)
            self._first_frames.pop(camera.id, None)
            self._failure_counts[camera.id] = self._failure_counts.get(camera.id, 0) + 1
            for rtsp_url in rtsp_urls:
                self._mark_open_attempt(camera.id, profile_name)
                retry_cap, retry_first_frame = _open_cap(rtsp_url, camera.id, profile)
                if retry_cap.isOpened():
                    if retry_first_frame is not None:
                        self._caps[camera.id] = retry_cap
                        self._caps_urls[camera.id] = rtsp_url
                        self._first_frames[camera.id] = retry_first_frame
                        self._last_fail_time.pop(camera.id, None)
                        self._failure_counts.pop(camera.id, None)
                        self._mark_success(camera.id)
                        return retry_first_frame
                    retry_ok, retry_frame = retry_cap.read()
                    if retry_ok and retry_frame is not None:
                        self._caps[camera.id] = retry_cap
                        self._caps_urls[camera.id] = rtsp_url
                        self._last_fail_time.pop(camera.id, None)
                        self._failure_counts.pop(camera.id, None)
                        self._mark_success(camera.id)
                        return retry_frame
                retry_cap.release()
                self._mark_open_failure(camera.id)
            return None

        self._mark_success(camera.id)
        return frame

    def release(self, camera_id: int) -> None:
        """Belirli bir kameranın VideoCapture'ını serbest bırakır."""
        if camera_id in self._caps:
            logger.info(f"[RTSP] Kamera {camera_id} capture serbest bırakıldı")
            self._caps[camera_id].release()
            del self._caps[camera_id]
        self._caps_urls.pop(camera_id, None)
        self._first_frames.pop(camera_id, None)
        self._last_fail_time.pop(camera_id, None)
        self._failure_counts.pop(camera_id, None)
        self._telemetry.pop(camera_id, None)

    def release_all(self) -> None:
        """Tüm açık akışları kapatır."""
        for cap in self._caps.values():
            cap.release()
        self._caps.clear()
        self._caps_urls.clear()
        self._first_frames.clear()
        self._last_fail_time.clear()
        self._failure_counts.clear()
        self._telemetry.clear()

    def get_camera_telemetry(self, camera: Camera) -> dict:
        """Bir kameranın RTSP açılış ve frame sağlığı için özet metrikleri döner."""
        if camera.id is None:
            return {}

        profile = self._select_warmup_profile(camera)
        telemetry = self._ensure_telemetry(camera.id)
        now = datetime.utcnow()
        last_frame_at = telemetry.get("last_frame_at")
        last_success_at = telemetry.get("last_success_at")
        last_failure_at = telemetry.get("last_failure_at")
        return {
            "camera_id": camera.id,
            "profile": telemetry.get("profile", self._select_profile_name(camera)),
            "open_attempts": telemetry.get("open_attempts", 0),
            "open_failures": telemetry.get("open_failures", 0),
            "failure_count": self._failure_counts.get(camera.id, 0),
            "retry_cooldown_seconds": self._current_retry_cooldown(camera.id, profile),
            "warmup_reads": profile.warmup_reads,
            "open_timeout_ms": profile.open_timeout_ms,
            "read_timeout_ms": profile.read_timeout_ms,
            "last_success_at": last_success_at,
            "last_failure_at": last_failure_at,
            "last_frame_at": last_frame_at,
            "last_frame_age_seconds": (now - last_frame_at).total_seconds() if last_frame_at else None,
            "last_success_age_seconds": (now - last_success_at).total_seconds() if last_success_at else None,
            "cached_first_frame": camera.id in self._first_frames,
            "has_capture": camera.id in self._caps and self._caps[camera.id].isOpened(),
        }
