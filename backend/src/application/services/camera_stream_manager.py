from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Optional, Set, Tuple

import asyncio
import cv2

from src.domain.entities.alarm import AlarmType
from src.domain.entities.camera import CameraStatus

logger = logging.getLogger(__name__)

PROFILE_FRAME_INTERVALS = {
    "grid": 0.25,      # 4 FPS
    "live": 1 / 15,    # 15 FPS
    "alarm": 0.5,      # 2 FPS
}


class CameraStreamManager:
    """
    Kamera başına TEK bir arka plan üretici (producer) task'ı çalıştırır:
    RTSP'den sürekli kare okur, bağlı tüm WebSocket istemcilerine (aynı ağdaki
    farklı cihazlar dahil) yayınlar (broadcast) ve AI açıksa kendi periyodunda
    (varsayılan ~2 FPS) insan tespiti yapar.

    Böylece kamera başına her zaman TEK RTSP bağlantısı açılır — kaç istemci
    izlerse izlesin ve AI açık olsun ya da olmasın; canlı izleme görüntü hızı
    AI'nın tespit hızına bağlı kalmaz (display_fps ile ayrı yönetilir).

    Producer, şu durumlarda çalışır:
      - en az bir izleyici (subscriber) varsa, VEYA
      - AI tespiti açıksa (izleyici olmasa da arka planda güvenlik taraması sürer)
    Aksi halde (AI kapalı + izleyici yok) producer durur — boşa RTSP çekilmez.
    """

    def __init__(
        self,
        ai_service,
        password_service=None,
        db_session_factory=None,
        camera_repository_factory=None,
        alarm_repository_factory=None,
        frame_source_factory=None,
        ai_interval: float = 0.5,
        display_fps: float = 15.0,
        cooldown_seconds: int = 60,
    ):
        self._ai_service = ai_service
        self._password_service = password_service
        self._db_session_factory = db_session_factory
        self._camera_repository_factory = camera_repository_factory
        self._alarm_repository_factory = alarm_repository_factory
        self._frame_source_factory = frame_source_factory
        self._ai_interval = ai_interval
        self._frame_interval = 1.0 / display_fps
        self._cooldown_seconds = cooldown_seconds

        self._producers: Dict[int, asyncio.Task] = {}
        self._stop_flags: Dict[int, bool] = {}
        self._subscribers: Dict[int, Set[asyncio.Queue]] = {}
        self._subscriber_profiles: Dict[int, Dict[asyncio.Queue, str]] = {}
        self._latest_messages: Dict[int, Tuple[float, dict]] = {}
        self._last_alarm_times: Dict[int, Dict[Tuple[int, AlarmType], datetime]] = {}
        self._last_ai_time: Dict[int, float] = {}
        self._active_ai_tasks: Dict[int, asyncio.Task] = {}
        self._ai_enabled_cache: Dict[int, bool] = {}
        self._idle_grace_seconds = 10.0
        self._executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="cam_stream")
        self._ai_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="cam_ai")

    def _new_frame_source(self):
        if self._frame_source_factory is None:
            raise RuntimeError("CameraStreamManager frame_source_factory yapılandırılmamış.")
        return self._frame_source_factory()

    def _open_db(self):
        if self._db_session_factory is None:
            raise RuntimeError("CameraStreamManager db_session_factory yapılandırılmamış.")
        return self._db_session_factory()

    def _camera_repo(self, db):
        if self._camera_repository_factory is None:
            raise RuntimeError("CameraStreamManager camera_repository_factory yapılandırılmamış.")
        return self._camera_repository_factory(db)

    def _alarm_repo(self, db):
        if self._alarm_repository_factory is None:
            raise RuntimeError("CameraStreamManager alarm_repository_factory yapılandırılmamış.")
        return self._alarm_repository_factory(db)

    # ------------------------------------------------------------------
    # İzleyici (subscriber) yönetimi — WebSocket bağlantıları buradan akar
    # ------------------------------------------------------------------

    async def subscribe(self, camera_id: int, profile: str = "grid") -> Optional[asyncio.Queue]:
        """Kamerayı izlemek isteyen bir istemciyi kaydeder ve kare kuyruğu döner.

        ACTIVE veya ERROR durumdaki kameralar için abonelik açılır. ERROR kameralar
        için producer çalışmaya devam eder; kamera toparlandığında kare otomatik
        akar. Yalnızca INACTIVE veya bulunamayan kameralar None döner.
        """
        loop = asyncio.get_event_loop()
        is_subscribable = await loop.run_in_executor(self._executor, lambda: self._sync_check_subscribable(camera_id))
        if not is_subscribable:
            return None

        queue: asyncio.Queue = asyncio.Queue(maxsize=2)
        self._subscribers.setdefault(camera_id, set()).add(queue)
        self._subscriber_profiles.setdefault(camera_id, {})[queue] = profile
        cached = self._latest_messages.get(camera_id)
        if cached and time.monotonic() - cached[0] <= 2.0:
            queue.put_nowait(cached[1])
        await self._ensure_producer(camera_id)
        return queue

    def unsubscribe(self, camera_id: int, queue: asyncio.Queue) -> None:
        """Bir istemcinin izlemesini sonlandırır. AI kapalıysa ve başka izleyici yoksa producer durur."""
        subs = self._subscribers.get(camera_id)
        if subs:
            subs.discard(queue)
            if not subs:
                self._subscribers.pop(camera_id, None)
        profiles = self._subscriber_profiles.get(camera_id)
        if profiles:
            profiles.pop(queue, None)
            if not profiles:
                self._subscriber_profiles.pop(camera_id, None)

    async def close_all(self, camera_id: int, reason: str) -> None:
        """Bir kameraya ait tüm açık izleme bağlantılarını anında kapatır.

        Admin kamerayı durdurduğunda/sildiğinde çağrılır — periyodik kontrolü
        beklemeden istemcileri haberdar eder.
        """
        subs = list(self._subscribers.get(camera_id, ()))
        for q in subs:
            try:
                q.put_nowait({"closed": True, "reason": reason})
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    q.put_nowait({"closed": True, "reason": reason})
                except asyncio.QueueFull:
                    pass
        self._subscribers.pop(camera_id, None)
        self._subscriber_profiles.pop(camera_id, None)
        self._latest_messages.pop(camera_id, None)
        self._stop_flags[camera_id] = True
        ai_task = self._active_ai_tasks.pop(camera_id, None)
        if ai_task and not ai_task.done():
            ai_task.cancel()

    # ------------------------------------------------------------------
    # Genel yönetim — uygulama başlangıcı/kapanışı, status/AI toggle route'ları
    # ------------------------------------------------------------------

    async def start_all_active(self) -> None:
        """Uygulama başlangıcında AI açık kameralar için producer'ı önceden başlatır."""
        db = self._open_db()
        try:
            repo = self._camera_repo(db)
            cameras = repo.list_all()
            total = len(cameras)
            active_count = sum(1 for c in cameras if c.status == CameraStatus.ACTIVE)
            logger.info(f"[StreamManager] Başlangıç: {total} kamera, {active_count} ACTIVE")
            started = 0
            for cam in cameras:
                logger.info(
                    f"[StreamManager]   Kamera {cam.id} '{cam.name}' "
                    f"status={cam.status.value} ai={cam.ai_detection_enabled} "
                    f"host={cam.host}:{cam.rtsp_port}{cam.rtsp_path or ''}"
                )
                if cam.status == CameraStatus.ACTIVE and cam.ai_detection_enabled:
                    await self._ensure_producer(cam.id)
                    started += 1
            if started:
                logger.info(f"[StreamManager] {started} kamera için arka plan tespiti başlatıldı.")
            else:
                logger.info("[StreamManager] Başlangıçta producer başlatılmadı (AI kapalı veya ACTIVE kamera yok).")
        finally:
            db.close()

    async def stop_all(self) -> None:
        """Uygulama kapanışında tüm producer'ları durdurur."""
        for camera_id in list(self._producers.keys()):
            self._stop_flags[camera_id] = True
        for camera_id, task in list(self._producers.items()):
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=3.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        for task in list(self._active_ai_tasks.values()):
            if not task.done():
                task.cancel()
        self._active_ai_tasks.clear()
        self._executor.shutdown(wait=False)
        self._ai_executor.shutdown(wait=False)
        logger.info("[StreamManager] Tüm kamera producer'ları durduruldu.")

    async def ensure_running_state(self, camera_id: int) -> None:
        """Kameranın güncel durumuna (status/AI) göre producer'ı başlatır veya durdurma sinyali verir.

        Status/AI toggle route'ları her değişiklikte bunu çağırır — producer'ın
        var olma gerekçesi (izleyici VAR ya da AI AÇIK) artık geçerli değilse durur.
        """
        loop = asyncio.get_event_loop()
        camera_state = await loop.run_in_executor(self._executor, lambda: self._sync_get_state(camera_id))
        if camera_state is None:
            self._stop_flags[camera_id] = True
            return

        status, ai_enabled = camera_state
        if status != CameraStatus.ACTIVE:
            self._stop_flags[camera_id] = True
            return

        needs_producer = ai_enabled or bool(self._subscribers.get(camera_id))
        if needs_producer:
            await self._ensure_producer(camera_id)
        else:
            self._stop_flags[camera_id] = True

    async def reset_stream(self, camera_id: int) -> None:
        """Kameranın aktif yayınını durdurur, soketini kapatır ve yeni bilgilerle yeniden başlatır."""
        # İstemcileri bilgilendir ve bağlantılarını sonlandır
        await self.close_all(camera_id, "Kamera bağlantı ayarları güncellendi, yeniden bağlanılıyor.")
        
        task = self._producers.get(camera_id)
        if task and not task.done():
            task.cancel()
            try:
                # Arka plan task'ının sonlanmasını ve soketi bırakmasını (release) bekle
                await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
            except Exception:
                pass
        ai_task = self._active_ai_tasks.pop(camera_id, None)
        if ai_task and not ai_task.done():
            ai_task.cancel()
        self._producers.pop(camera_id, None)
        # Yeni bağlantı parametrelerine göre yayını tekrar başlat
        await self.ensure_running_state(camera_id)

    # ------------------------------------------------------------------
    # Producer döngüsü
    # ------------------------------------------------------------------

    async def _ensure_producer(self, camera_id: int) -> None:
        task = self._producers.get(camera_id)
        if task is not None and not task.done():
            self._stop_flags[camera_id] = False
            return
        self._stop_flags[camera_id] = False
        self._producers[camera_id] = asyncio.create_task(
            self._producer_loop(camera_id), name=f"cam_stream_{camera_id}"
        )
        logger.info(f"[StreamManager] Kamera {camera_id} için producer başlatıldı.")

    async def _producer_loop(self, camera_id: int) -> None:
        frame_source = self._new_frame_source()
        loop = asyncio.get_event_loop()
        idle_since: float | None = None

        try:
            while not self._stop_flags.get(camera_id, False):
                t0 = loop.time()
                try:
                    frame, camera_active = await loop.run_in_executor(
                        self._executor, lambda: self._read_frame_sync(camera_id, frame_source)
                    )
                except Exception as exc:
                    logger.warning(f"[StreamManager] Kamera {camera_id} kare okuma hatası: {exc}")
                    frame, camera_active = None, True

                if not camera_active:
                    logger.info(f"[StreamManager] Kamera {camera_id} pasif/silinmiş — producer durduruluyor.")
                    break

                alarm = None
                if frame is not None:
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ret:
                        self._broadcast(camera_id, {
                            "frame": buffer.tobytes(),
                            "alarm_triggered": False,
                            "alarm_id": None,
                        })
                    else:
                        logger.debug(f"[StreamManager] Kamera {camera_id} frame encode başarısız")
                else:
                    logger.debug(f"[StreamManager] Kamera {camera_id} frame=None (bağlantı kuruluyor veya hatalı)")

                has_subscribers = bool(self._subscribers.get(camera_id))
                ai_enabled = self._sync_check_ai_enabled_cached(camera_id)
                should_run_ai = frame is not None and ai_enabled and self._should_run_ai(camera_id)

                if should_run_ai:
                    self._last_ai_time[camera_id] = loop.time()
                    self._schedule_ai_detection(camera_id, frame.copy())

                # AI kapalı ve hiç izleyici yoksa RTSP oturumunu kısa bir süre sıcak tut.
                if not has_subscribers and not ai_enabled:
                    if idle_since is None:
                        idle_since = loop.time()
                    elif loop.time() - idle_since >= self._idle_grace_seconds:
                        break
                else:
                    idle_since = None

                elapsed = loop.time() - t0
                await asyncio.sleep(max(0.0, self._effective_frame_interval(camera_id) - elapsed))
        except asyncio.CancelledError:
            pass
        finally:
            frame_source.release(camera_id)
            self._producers.pop(camera_id, None)

    def _should_run_ai(self, camera_id: int) -> bool:
        """AI taramasının bu turda tetiklenmeye uygun olup olmadığını döner."""
        now = time.monotonic()
        last = self._last_ai_time.get(camera_id, 0.0)
        if now - last < self._ai_interval:
            return False
        task = self._active_ai_tasks.get(camera_id)
        return task is None or task.done()

    def _schedule_ai_detection(self, camera_id: int, frame) -> None:
        """AI tespitini capture döngüsünden ayırıp arka planda çalıştırır."""
        loop = asyncio.get_running_loop()

        async def _runner() -> None:
            try:
                alarm = await loop.run_in_executor(self._ai_executor, lambda: self._detect_and_alarm_sync(camera_id, frame))
                if alarm:
                    logger.info(
                        f"[StreamManager] Kamera {camera_id} — insan tespiti! "
                        f"Güven: %{int(alarm.confidence * 100)}, Alarm ID: {alarm.id}"
                    )
                    self._broadcast(camera_id, {
                        "frame": None,
                        "alarm_triggered": True,
                        "alarm_id": alarm.id,
                    })
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.warning(f"[StreamManager] Kamera {camera_id} AI görevi hatası: {exc}")
            finally:
                current = self._active_ai_tasks.get(camera_id)
                if current is asyncio.current_task():
                    self._active_ai_tasks.pop(camera_id, None)

        task = asyncio.create_task(_runner(), name=f"cam_ai_{camera_id}")
        self._active_ai_tasks[camera_id] = task

    def _effective_frame_interval(self, camera_id: int) -> float:
        """Mevcut istemci profillerine göre üretici döngüsünün alt sınırını döner."""
        profiles = self._subscriber_profiles.get(camera_id, {})
        if profiles:
            selected = min(
                (PROFILE_FRAME_INTERVALS.get(profile, self._frame_interval) for profile in profiles.values()),
                default=self._frame_interval,
            )
            return selected
        if self._sync_check_ai_enabled_cached(camera_id):
            return self._ai_interval
        return self._frame_interval

    def _effective_profile_name(self, camera_id: int) -> str:
        """İzleyici profillerinden seçilmiş etkin akış profilini döner."""
        profiles = self._subscriber_profiles.get(camera_id, {})
        if not profiles:
            return "idle"
        weights = {"alarm": 1, "grid": 2, "live": 3}
        selected = "alarm"
        for profile in profiles.values():
            if weights.get(profile, 0) > weights.get(selected, 0):
                selected = profile
        return selected

    def _broadcast(self, camera_id: int, message: dict) -> None:
        self._latest_messages[camera_id] = (time.monotonic(), message)
        for q in list(self._subscribers.get(camera_id, ())):
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass

    # ------------------------------------------------------------------
    # Bloklayıcı (senkron) işlemler — ThreadPoolExecutor içinde çalışır
    # ------------------------------------------------------------------

    def _sync_check_subscribable(self, camera_id: int) -> bool:
        """ACTIVE veya ERROR durumdaki kameralara abonelik izni verir; INACTIVE → False."""
        db = self._open_db()
        try:
            repo = self._camera_repo(db)
            cam = repo.get_by_id(camera_id)
            return cam is not None and cam.status in (CameraStatus.ACTIVE, CameraStatus.ERROR)
        finally:
            db.close()

    def _sync_get_state(self, camera_id: int) -> Optional[Tuple[CameraStatus, bool]]:
        db = self._open_db()
        try:
            repo = self._camera_repo(db)
            cam = repo.get_by_id(camera_id)
            if not cam:
                return None
            return cam.status, cam.ai_detection_enabled
        finally:
            db.close()

    def _sync_check_ai_enabled_cached(self, camera_id: int) -> bool:
        """Son işlenen kare sırasında öğrenilen AI durumunu döner (ekstra DB sorgusu yok)."""
        return self._ai_enabled_cache.get(camera_id, False)

    def get_runtime_telemetry(self, camera_id: int) -> dict:
        """Canlı akış üreticisinin çalışma durumunu özetler."""
        cached = self._latest_messages.get(camera_id)
        last_broadcast_at = cached[0] if cached else None
        now = time.monotonic()
        producer_task = self._producers.get(camera_id)
        ai_task = self._active_ai_tasks.get(camera_id)
        subscriber_count = len(self._subscribers.get(camera_id, ()))
        return {
            "producer_running": bool(producer_task and not producer_task.done()),
            "subscriber_count": subscriber_count,
            "active_profile": self._effective_profile_name(camera_id),
            "ai_task_running": bool(ai_task and not ai_task.done()),
            "cached_frame_available": cached is not None,
            "last_broadcast_age_seconds": (now - last_broadcast_at) if last_broadcast_at else None,
            "last_broadcast_at_monotonic": last_broadcast_at,
        }

    def _read_frame_sync(self, camera_id: int, frame_source) -> tuple:
        """Bloklayıcı RTSP okuma.

        Kendi DB session'ını açar/kapatır — thread pool'dan güvenle çağrılabilir.
        Döner: (frame | None, camera_active: bool)
        """
        from src.application.use_cases.frame_processing_use_case import ProcessFrameUseCase

        db = self._open_db()
        try:
            camera_repo = self._camera_repo(db)

            camera = camera_repo.get_by_id(camera_id)
            if not camera or camera.status == CameraStatus.INACTIVE:
                return None, False

            self._ai_enabled_cache[camera_id] = camera.ai_detection_enabled

            use_case = ProcessFrameUseCase(
                camera_repository=camera_repo,
                alarm_repository=None,
                frame_source=frame_source,
                ai_service=self._ai_service,
                cooldown_seconds=self._cooldown_seconds,
            )

            # Önceden yüklenmiş kamera objesi geçiriliyor — çift DB sorgusunu önler
            frame = use_case.read_frame(camera_id, camera=camera)
            if frame is None:
                return None, True

            return frame, True
        finally:
            db.close()

    def _detect_and_alarm_sync(self, camera_id: int, frame) -> Optional[object]:
        """Önceden okunmuş kare üzerinde AI tespiti ve alarm üretimi yapar."""
        from src.application.use_cases.frame_processing_use_case import ProcessFrameUseCase

        db = self._open_db()
        try:
            camera_repo = self._camera_repo(db)
            alarm_repo = self._alarm_repo(db)
            camera = camera_repo.get_by_id(camera_id)
            if not camera or not camera.ai_detection_enabled or camera.status != CameraStatus.ACTIVE:
                return None

            use_case = ProcessFrameUseCase(
                camera_repository=camera_repo,
                alarm_repository=alarm_repo,
                frame_source=None,
                ai_service=self._ai_service,
                cooldown_seconds=self._cooldown_seconds,
            )
            use_case._last_alarms = dict(self._last_alarm_times.get(camera_id, {}))
            alarm = use_case.detect_and_alarm(camera_id, frame)
            self._last_alarm_times[camera_id] = dict(use_case._last_alarms)
            return alarm
        finally:
            db.close()
