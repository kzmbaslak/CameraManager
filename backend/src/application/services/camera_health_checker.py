"""
Kameraların erişilebilirliğini periyodik TCP bağlantı testi (ping) ile kontrol eden servis.

AI tespiti kapalı veya hiç izlenmiyor olsa bile çalışır — Dashboard'daki
çevrimiçi/çevrimdışı durumu, kullanıcı kamerayı izlemese dahi güncel tutar.
"""
from __future__ import annotations

import asyncio
import logging
import socket
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CameraHealthChecker:
    """status != 'inactive' olan tüm kameralara periyodik TCP ping atar."""

    def __init__(
        self,
        check_interval: float = 10.0,
        timeout: float = 3.0,
        cooldown_seconds: int = 60,
        db_session_factory=None,
        camera_repository_factory=None,
        alarm_repository_factory=None,
        health_repository_factory=None,
    ):
        self._check_interval = check_interval
        self._timeout = timeout
        self._cooldown_seconds = cooldown_seconds
        self._db_session_factory = db_session_factory
        self._camera_repository_factory = camera_repository_factory
        self._alarm_repository_factory = alarm_repository_factory
        self._health_repository_factory = health_repository_factory
        self._task: asyncio.Task | None = None
        self._last_offline_alarm: Dict[int, datetime] = {}

    def _open_db(self):
        if self._db_session_factory is None:
            raise RuntimeError("CameraHealthChecker db_session_factory yapılandırılmamış.")
        return self._db_session_factory()

    def _camera_repo(self, db):
        if self._camera_repository_factory is None:
            raise RuntimeError("CameraHealthChecker camera_repository_factory yapılandırılmamış.")
        return self._camera_repository_factory(db)

    def _alarm_repo(self, db):
        if self._alarm_repository_factory is None:
            raise RuntimeError("CameraHealthChecker alarm_repository_factory yapılandırılmamış.")
        return self._alarm_repository_factory(db)

    def _health_repo(self, db):
        """Saglik gecmisi repository'si yapilandirildiysa dondurur."""
        if self._health_repository_factory is None:
            return None
        return self._health_repository_factory(db)

    def start(self) -> None:
        """Arka plan döngüsünü başlatır (zaten çalışıyorsa atlar)."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="camera_health_checker")
            logger.info("[HealthChecker] Kamera erişilebilirlik kontrolü başlatıldı.")

    def stop(self) -> None:
        """Arka plan döngüsünü durdurur."""
        if self._task and not self._task.done():
            self._task.cancel()

    async def _loop(self) -> None:
        loop = asyncio.get_event_loop()
        try:
            while True:
                try:
                    await loop.run_in_executor(None, self._check_all_sync)
                except Exception as exc:
                    logger.warning(f"[HealthChecker] Kontrol döngüsü hatası: {exc}")
                await asyncio.sleep(self._check_interval)
        except asyncio.CancelledError:
            pass

    def _ping(self, host: str, port: int) -> Tuple[bool, Optional[float], Optional[str]]:
        """TCP bağlantısı kurulabiliyor mu — kamera/NVR portunun açık olup olmadığını test eder."""
        try:
            started_at = time.monotonic()
            with socket.create_connection((host, port), timeout=self._timeout):
                return True, (time.monotonic() - started_at) * 1000, None
        except OSError as exc:
            return False, None, exc.__class__.__name__

    def _check_all_sync(self) -> None:
        from src.domain.entities.camera import CameraStatus
        from src.domain.entities.alarm import Alarm, AlarmSeverity, AlarmType, AlarmStatus

        db = self._open_db()
        try:
            camera_repo = self._camera_repo(db)
            alarm_repo = self._alarm_repo(db)
            health_repo = self._health_repo(db)

            cameras = [c for c in camera_repo.list_all() if c.status != CameraStatus.INACTIVE]

            for camera in cameras:
                reachable, latency_ms, failure_reason = self._ping(camera.host, camera.rtsp_port)
                now = datetime.utcnow()
                if health_repo is not None:
                    from src.domain.entities.camera_health import CameraHealthSample

                    health_repo.add(CameraHealthSample(
                        id=None,
                        camera_id=camera.id,
                        checked_at=now,
                        reachable=reachable,
                        status="reachable" if reachable else "unreachable",
                        latency_ms=latency_ms,
                        failure_reason=failure_reason,
                    ))
                    health_repo.prune_older_than(days=7)

                if reachable:
                    # TCP ping başarılı ama bu RTSP stream'in çalıştığını garanti etmez;
                    # özellikle NVR kanalları için NVR'ın portu her zaman açık kalır.
                    # ERROR→ACTIVE geçişi producer döngüsüne bırakılıyor: gerçek frame
                    # okunduğunda read_frame() status'u güncelliyor ve alarmı çözüyor.
                    continue

                # Erişilemiyor — durumu 'error' yap
                if camera.status != CameraStatus.ERROR:
                    camera.mark_error()
                    camera_repo.update(camera)

                # Tekrarlı alarm spamini önle (cooldown)
                last = self._last_offline_alarm.get(camera.id)
                if last is None or (now - last).total_seconds() >= self._cooldown_seconds:
                    alarm = Alarm(
                        id=None,
                        camera_id=camera.id,
                        alarm_type=AlarmType.CAMERA_OFFLINE,
                        status=AlarmStatus.NEW,
                        confidence=1.0,
                        bounding_box=None,
                        snapshot_path=None,
                        severity=AlarmSeverity.HIGH,
                        message="Kamera erişilemiyor (bağlantı testi başarısız)!",
                        created_at=now,
                    )
                    alarm_repo.add(alarm)
                    self._last_offline_alarm[camera.id] = now
        finally:
            db.close()
