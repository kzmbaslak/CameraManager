"""
Kameraların erişilebilirliğini periyodik TCP bağlantı testi (ping) ile kontrol eden servis.

AI tespiti kapalı veya hiç izlenmiyor olsa bile çalışır — Dashboard'daki
çevrimiçi/çevrimdışı durumu, kullanıcı kamerayı izlemese dahi güncel tutar.
"""
from __future__ import annotations

import asyncio
import logging
import socket
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


class CameraHealthChecker:
    """status != 'inactive' olan tüm kameralara periyodik TCP ping atar."""

    def __init__(self, check_interval: float = 10.0, timeout: float = 3.0, cooldown_seconds: int = 60):
        self._check_interval = check_interval
        self._timeout = timeout
        self._cooldown_seconds = cooldown_seconds
        self._task: asyncio.Task | None = None
        self._last_offline_alarm: Dict[int, datetime] = {}

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

    def _ping(self, host: str, port: int) -> bool:
        """TCP bağlantısı kurulabiliyor mu — kamera/NVR portunun açık olup olmadığını test eder."""
        try:
            with socket.create_connection((host, port), timeout=self._timeout):
                return True
        except OSError:
            return False

    def _check_all_sync(self) -> None:
        from src.infrastructure.database.database import SessionLocal
        from src.infrastructure.database.repositories.camera_repository import SqlAlchemyCameraRepository
        from src.infrastructure.database.repositories.alarm_repository import SqlAlchemyAlarmRepository
        from src.domain.entities.camera import CameraStatus
        from src.domain.entities.alarm import Alarm, AlarmType, AlarmStatus

        db = SessionLocal()
        try:
            camera_repo = SqlAlchemyCameraRepository(db)
            alarm_repo = SqlAlchemyAlarmRepository(db)

            cameras = [c for c in camera_repo.list_all() if c.status != CameraStatus.INACTIVE]

            for camera in cameras:
                reachable = self._ping(camera.host, camera.rtsp_port)

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
                now = datetime.utcnow()
                if last is None or (now - last).total_seconds() >= self._cooldown_seconds:
                    alarm = Alarm(
                        id=None,
                        camera_id=camera.id,
                        alarm_type=AlarmType.CAMERA_OFFLINE,
                        status=AlarmStatus.NEW,
                        confidence=1.0,
                        bounding_box=None,
                        snapshot_path=None,
                        message="Kamera erişilemiyor (bağlantı testi başarısız)!",
                        created_at=now,
                    )
                    alarm_repo.add(alarm)
                    self._last_offline_alarm[camera.id] = now
        finally:
            db.close()
