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
        self._last_degraded_alarm: Dict[int, datetime] = {}

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

    def _health_degradation(self, samples) -> tuple[bool, str, object]:
        from src.domain.entities.alarm import AlarmSeverity

        if not samples:
            return False, "", AlarmSeverity.LOW
        latest = samples[0]
        if not latest.reachable:
            return False, "", AlarmSeverity.LOW

        sample_count = len(samples)
        reachable_count = sum(1 for sample in samples if sample.reachable)
        availability = (reachable_count / sample_count) * 100 if sample_count else 100.0
        if availability < 90:
            return True, f"Kamera saglik uyarisi: erisilebilirlik %{availability:.1f}.", AlarmSeverity.HIGH
        if availability < 98:
            return True, f"Kamera saglik uyarisi: erisilebilirlik %{availability:.1f}.", AlarmSeverity.MEDIUM
        if latest.latency_ms is not None and latest.latency_ms > 1000:
            return True, f"Kamera saglik uyarisi: yuksek latency {latest.latency_ms:.0f} ms.", AlarmSeverity.MEDIUM
        return False, "", AlarmSeverity.LOW

    def _resolve_open_health_degraded(self, alarm_repo, camera_id: int, now: datetime, reason: str) -> None:
        from src.domain.entities.alarm import AlarmStatus, AlarmType

        alarms = alarm_repo.list_all(camera_id=camera_id, alarm_type=AlarmType.CAMERA_HEALTH_DEGRADED, limit=20)
        for alarm in alarms:
            if alarm.status == AlarmStatus.RESOLVED:
                continue
            alarm.resolution_reason = reason
            alarm.resolve(now)
            alarm_repo.update(alarm)

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
                    if health_repo is not None:
                        samples = list(health_repo.list_recent(camera.id, 120))
                        degraded, message, severity = self._health_degradation(samples)
                        if degraded:
                            has_open_degraded = any(
                                alarm.status != AlarmStatus.RESOLVED
                                for alarm in alarm_repo.list_all(
                                    camera_id=camera.id,
                                    alarm_type=AlarmType.CAMERA_HEALTH_DEGRADED,
                                    limit=20,
                                )
                            )
                            last_degraded = self._last_degraded_alarm.get(camera.id)
                            if (
                                not has_open_degraded
                                and (last_degraded is None or (now - last_degraded).total_seconds() >= self._cooldown_seconds)
                            ):
                                alarm_repo.add(Alarm(
                                    id=None,
                                    camera_id=camera.id,
                                    alarm_type=AlarmType.CAMERA_HEALTH_DEGRADED,
                                    status=AlarmStatus.NEW,
                                    confidence=None,
                                    bounding_box=None,
                                    snapshot_path=None,
                                    severity=severity,
                                    message=message,
                                    created_at=now,
                                ))
                                self._last_degraded_alarm[camera.id] = now
                        else:
                            self._resolve_open_health_degraded(
                                alarm_repo,
                                camera.id,
                                now,
                                "Kamera saglik metrikleri normale dondu.",
                            )
                    # TCP ping başarılı ama bu RTSP stream'in çalıştığını garanti etmez;
                    # özellikle NVR kanalları için NVR'ın portu her zaman açık kalır.
                    # ERROR→ACTIVE geçişi producer döngüsüne bırakılıyor: gerçek frame
                    # okunduğunda read_frame() status'u güncelliyor ve alarmı çözüyor.
                    continue

                # Erişilemiyor — durumu 'error' yap
                if camera.status != CameraStatus.ERROR:
                    camera.mark_error()
                    camera_repo.update(camera)
                self._resolve_open_health_degraded(
                    alarm_repo,
                    camera.id,
                    now,
                    "Kamera cevrimdisi alarmi saglik uyarisi yerine gecti.",
                )

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
