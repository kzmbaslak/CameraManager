from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Set, Tuple

import asyncio
import cv2

from src.application.services.camera_tamper_policy import CameraTamperAnalysisResult, CameraTamperPolicy
from src.application.services.person_density_policy import PersonDensityPolicy
from src.domain.entities.alarm import Alarm, AlarmSeverity, AlarmStatus, AlarmType
from src.domain.entities.camera import CameraStatus
from src.domain.entities.recording_segment import RecordingSegment
from src.infrastructure.recording.retention import recording_storage_dir
from src.infrastructure.time_utils import utc_now

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
        recording_repository_factory=None,
        person_analytics_repository_factory=None,
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
        self._recording_repository_factory = recording_repository_factory
        self._person_analytics_repository_factory = person_analytics_repository_factory
        self._frame_source_factory = frame_source_factory
        self._ai_interval = ai_interval
        self._frame_interval = 1.0 / display_fps
        self._cooldown_seconds = cooldown_seconds
        self._camera_tamper_policy = CameraTamperPolicy.from_environment()
        self._person_density_policy = PersonDensityPolicy.from_environment()

        self._producers: Dict[int, asyncio.Task] = {}
        self._stop_flags: Dict[int, bool] = {}
        self._subscribers: Dict[int, Set[asyncio.Queue]] = {}
        self._subscriber_profiles: Dict[int, Dict[asyncio.Queue, str]] = {}
        self._latest_messages: Dict[int, Tuple[float, dict]] = {}
        self._frame_broadcast_times: Dict[int, deque[float]] = {}
        self._producer_started_at: Dict[int, datetime] = {}
        self._producer_started_at_monotonic: Dict[int, float] = {}
        self._producer_start_counts: Dict[int, int] = {}
        self._last_alarm_times: Dict[int, Dict[Tuple[int, AlarmType], datetime]] = {}
        self._last_ai_time: Dict[int, float] = {}
        self._active_ai_tasks: Dict[int, asyncio.Task] = {}
        self._active_motion_tasks: Dict[int, asyncio.Task] = {}
        self._active_tamper_tasks: Dict[int, asyncio.Task] = {}
        self._ai_enabled_cache: Dict[int, bool] = {}
        self._motion_enabled_cache: Dict[int, bool] = {}
        self._ai_frame_stride_cache: Dict[int, int] = {}
        self._ai_frame_counters: Dict[int, int] = {}
        self._motion_frame_counters: Dict[int, int] = {}
        self._tamper_frame_counters: Dict[int, int] = {}
        self._tamper_suspicious_counts: Dict[int, int] = {}
        self._motion_previous_frames: Dict[int, object] = {}
        self._latest_detection_messages: Dict[int, Tuple[float, dict]] = {}
        self._recording_buffers: Dict[int, deque[Tuple[float, object]]] = {}
        self._continuous_recording_buffers: Dict[int, deque[Tuple[float, object]]] = {}
        self._continuous_recording_started_at: Dict[int, float] = {}
        self._last_continuous_recording_frame_at: Dict[int, float] = {}
        self._last_ai_inference_ms: Dict[int, float] = {}
        self._avg_ai_inference_ms: Dict[int, float] = {}
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

    def _recording_repo(self, db):
        if self._recording_repository_factory is None:
            raise RuntimeError("CameraStreamManager recording_repository_factory yapilandirilmamis.")
        return self._recording_repository_factory(db)

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
        self._frame_broadcast_times.pop(camera_id, None)
        self._stop_flags[camera_id] = True
        ai_task = self._active_ai_tasks.pop(camera_id, None)
        if ai_task and not ai_task.done():
            ai_task.cancel()
        motion_task = self._active_motion_tasks.pop(camera_id, None)
        if motion_task and not motion_task.done():
            motion_task.cancel()
        tamper_task = self._active_tamper_tasks.pop(camera_id, None)
        if tamper_task and not tamper_task.done():
            tamper_task.cancel()
        self._motion_previous_frames.pop(camera_id, None)
        self._tamper_suspicious_counts.pop(camera_id, None)

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
                if cam.status == CameraStatus.ACTIVE and (
                    cam.ai_detection_enabled or cam.motion_detection_enabled or self._continuous_recording_enabled_for_camera(cam)
                ):
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
        for task in list(self._active_motion_tasks.values()):
            if not task.done():
                task.cancel()
        self._active_motion_tasks.clear()
        for task in list(self._active_tamper_tasks.values()):
            if not task.done():
                task.cancel()
        self._active_tamper_tasks.clear()
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

        status, ai_enabled, motion_enabled, continuous_recording_enabled = camera_state
        if status != CameraStatus.ACTIVE:
            self._stop_flags[camera_id] = True
            return

        needs_producer = ai_enabled or motion_enabled or continuous_recording_enabled or bool(self._subscribers.get(camera_id))
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
        motion_task = self._active_motion_tasks.pop(camera_id, None)
        if motion_task and not motion_task.done():
            motion_task.cancel()
        tamper_task = self._active_tamper_tasks.pop(camera_id, None)
        if tamper_task and not tamper_task.done():
            tamper_task.cancel()
        self._motion_previous_frames.pop(camera_id, None)
        self._tamper_suspicious_counts.pop(camera_id, None)
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
        self._producer_started_at[camera_id] = utc_now()
        self._producer_started_at_monotonic[camera_id] = time.monotonic()
        self._producer_start_counts[camera_id] = self._producer_start_counts.get(camera_id, 0) + 1
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
                    frame, camera_active, ai_enabled, motion_enabled, ai_frame_stride, continuous_recording_enabled = await loop.run_in_executor(
                        self._executor, lambda: self._read_frame_sync(camera_id, frame_source)
                    )
                except Exception as exc:
                    logger.warning(f"[StreamManager] Kamera {camera_id} kare okuma hatası: {exc}")
                    frame, camera_active, ai_enabled, motion_enabled, ai_frame_stride, continuous_recording_enabled = None, True, self._sync_check_ai_enabled_cached(camera_id), self._sync_check_motion_enabled_cached(camera_id), 1, False

                if not camera_active:
                    logger.info(f"[StreamManager] Kamera {camera_id} pasif/silinmiş — producer durduruluyor.")
                    break

                if frame is not None:
                    self._append_recording_frame(camera_id, frame)
                    self._handle_continuous_recording_frame(camera_id, frame, continuous_recording_enabled)
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ret:
                        self._broadcast(camera_id, {
                            "frame": buffer.tobytes(),
                            "alarm_triggered": False,
                            "alarm_id": None,
                            **self._recent_detection_payload(camera_id),
                        })
                    else:
                        logger.debug(f"[StreamManager] Kamera {camera_id} frame encode başarısız")
                else:
                    logger.debug(f"[StreamManager] Kamera {camera_id} frame=None (bağlantı kuruluyor veya hatalı)")

                has_subscribers = bool(self._subscribers.get(camera_id))
                should_run_ai = frame is not None and ai_enabled and self._should_run_ai(camera_id, ai_frame_stride)
                should_run_motion = frame is not None and motion_enabled and self._should_run_motion(camera_id)
                should_run_tamper = frame is not None and self._should_run_tamper(camera_id)

                if should_run_ai:
                    self._last_ai_time[camera_id] = loop.time()
                    self._schedule_ai_detection(camera_id, frame.copy())
                if should_run_tamper:
                    self._schedule_tamper_detection(camera_id, frame.copy())
                if frame is not None and motion_enabled:
                    previous_frame = self._motion_previous_frames.get(camera_id)
                    if should_run_motion and previous_frame is not None:
                        self._schedule_motion_detection(camera_id, previous_frame.copy(), frame.copy())
                    self._motion_previous_frames[camera_id] = frame.copy()
                elif not motion_enabled:
                    self._motion_previous_frames.pop(camera_id, None)

                # AI kapalı ve hiç izleyici yoksa RTSP oturumunu kısa bir süre sıcak tut.
                if not has_subscribers and not ai_enabled and not motion_enabled and not continuous_recording_enabled:
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
            self._motion_previous_frames.pop(camera_id, None)
            self._tamper_suspicious_counts.pop(camera_id, None)

    def _should_run_ai(self, camera_id: int, frame_stride: int = 1) -> bool:
        """AI taramasının bu turda tetiklenmeye uygun olup olmadığını döner."""
        stride = max(1, frame_stride)
        self._ai_frame_counters[camera_id] = self._ai_frame_counters.get(camera_id, 0) + 1
        if (self._ai_frame_counters[camera_id] - 1) % stride != 0:
            return False
        now = time.monotonic()
        last = self._last_ai_time.get(camera_id, 0.0)
        if now - last < self._ai_interval:
            return False
        task = self._active_ai_tasks.get(camera_id)
        return task is None or task.done()

    def _motion_frame_stride(self) -> int:
        try:
            value = int(os.environ.get("MOTION_DETECTION_FRAME_STRIDE", "5") or "5")
        except ValueError:
            value = 5
        return min(max(value, 1), 60)

    def _should_run_motion(self, camera_id: int) -> bool:
        """Basit hareket analizinin bu turda calisip calismayacagini dondurur."""
        stride = self._motion_frame_stride()
        self._motion_frame_counters[camera_id] = self._motion_frame_counters.get(camera_id, 0) + 1
        if (self._motion_frame_counters[camera_id] - 1) % stride != 0:
            return False
        task = self._active_motion_tasks.get(camera_id)
        return task is None or task.done()

    def _should_run_tamper(self, camera_id: int) -> bool:
        """Kamera sabotaj analizinin bu turda calisip calismayacagini dondurur."""
        if not self._camera_tamper_policy.enabled:
            return False
        self._tamper_frame_counters[camera_id] = self._tamper_frame_counters.get(camera_id, 0) + 1
        if (self._tamper_frame_counters[camera_id] - 1) % self._camera_tamper_policy.frame_stride != 0:
            return False
        task = self._active_tamper_tasks.get(camera_id)
        return task is None or task.done()

    def _schedule_tamper_detection(self, camera_id: int, frame) -> None:
        """Kamera karartma/kapama/bulaniklastirma analizini arka planda calistirir."""
        loop = asyncio.get_running_loop()

        async def _runner() -> None:
            try:
                alarm, result = await loop.run_in_executor(
                    self._ai_executor,
                    lambda: self._detect_tamper_and_alarm_sync(camera_id, frame),
                )
                if alarm is None or result is None:
                    return
                detection_payload = self._serialize_tamper_result(result)
                self._broadcast(camera_id, {
                    "frame": None,
                    "alarm_triggered": True,
                    "alarm_id": alarm.id,
                    **detection_payload,
                })
                logger.warning(
                    "[StreamManager] Kamera %s sabotaj supheli: %s, Alarm ID: %s",
                    camera_id,
                    result.reason,
                    alarm.id,
                )
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.warning(f"[StreamManager] Kamera {camera_id} sabotaj analiz gorevi hatasi: {exc}")
            finally:
                current = self._active_tamper_tasks.get(camera_id)
                if current is asyncio.current_task():
                    self._active_tamper_tasks.pop(camera_id, None)

        task = asyncio.create_task(_runner(), name=f"cam_tamper_{camera_id}")
        self._active_tamper_tasks[camera_id] = task

    def _schedule_motion_detection(self, camera_id: int, previous_frame, current_frame) -> None:
        """Hareket analizini capture dongusunden ayirip arka planda calistirir."""
        loop = asyncio.get_running_loop()

        async def _runner() -> None:
            try:
                result = await loop.run_in_executor(
                    self._ai_executor,
                    lambda: self._detect_motion_and_alarm_sync(camera_id, previous_frame, current_frame),
                )
                if result is None or result.alarm is None:
                    return
                alarm = result.alarm
                detection_payload = self._serialize_motion_result(result)
                self._broadcast(camera_id, {
                    "frame": None,
                    "alarm_triggered": True,
                    "alarm_id": alarm.id,
                    **detection_payload,
                })
                post_seconds = self._event_post_seconds()
                if post_seconds > 0:
                    await asyncio.sleep(post_seconds)
                clip_frames = self._recording_clip_frames(camera_id)
                if clip_frames:
                    await loop.run_in_executor(
                        self._executor,
                        lambda: self._save_event_recording_clip_sync(camera_id, alarm.id, clip_frames, detection_payload),
                    )
                logger.info(
                    "[StreamManager] Kamera %s hareket tespiti! Degisen alan: %%%s, Alarm ID: %s",
                    camera_id,
                    int(result.motion_ratio * 100),
                    alarm.id,
                )
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.warning(f"[StreamManager] Kamera {camera_id} hareket gorevi hatasi: {exc}")
            finally:
                current = self._active_motion_tasks.get(camera_id)
                if current is asyncio.current_task():
                    self._active_motion_tasks.pop(camera_id, None)

        task = asyncio.create_task(_runner(), name=f"cam_motion_{camera_id}")
        self._active_motion_tasks[camera_id] = task

    def _schedule_ai_detection(self, camera_id: int, frame) -> None:
        """AI tespitini capture döngüsünden ayırıp arka planda çalıştırır."""
        loop = asyncio.get_running_loop()

        async def _runner() -> None:
            try:
                result = await loop.run_in_executor(self._ai_executor, lambda: self._detect_and_alarm_sync(camera_id, frame))
                if result is None:
                    return
                if result.inference_ms is not None:
                    self._last_ai_inference_ms[camera_id] = result.inference_ms
                    previous_avg = self._avg_ai_inference_ms.get(camera_id)
                    self._avg_ai_inference_ms[camera_id] = (
                        result.inference_ms if previous_avg is None else (previous_avg * 0.8) + (result.inference_ms * 0.2)
                    )
                alarm = result.alarm
                detection_payload = self._serialize_detection_result(result)
                if detection_payload["detections"]:
                    await loop.run_in_executor(
                        self._executor,
                        lambda: self._record_person_analytics_sync(camera_id, detection_payload),
                    )
                    self._latest_detection_messages[camera_id] = (time.monotonic(), detection_payload)
                    self._broadcast(camera_id, {
                        "frame": None,
                        "alarm_triggered": bool(alarm),
                        "alarm_id": alarm.id if alarm else None,
                        **detection_payload,
                    })
                if alarm:
                    post_seconds = self._event_post_seconds()
                    if post_seconds > 0:
                        await asyncio.sleep(post_seconds)
                    clip_frames = self._recording_clip_frames(camera_id)
                    if clip_frames:
                        await loop.run_in_executor(
                            self._executor,
                            lambda: self._save_event_recording_clip_sync(camera_id, alarm.id, clip_frames, detection_payload),
                        )
                    logger.info(
                        f"[StreamManager] Kamera {camera_id} — insan tespiti! "
                        f"Güven: %{int(alarm.confidence * 100)}, Alarm ID: {alarm.id}"
                    )
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
        if self._sync_check_ai_enabled_cached(camera_id) or self._sync_check_motion_enabled_cached(camera_id):
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
        if message.get("frame") is not None:
            self._mark_frame_broadcast(camera_id)
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

    def _event_clip_seconds(self) -> float:
        try:
            value = float(os.environ.get("RECORDING_EVENT_CLIP_SECONDS", "6") or "6")
        except ValueError:
            value = 6.0
        return min(max(value, 1.0), 30.0)

    def _event_pre_seconds(self) -> float:
        try:
            value = float(os.environ.get("RECORDING_EVENT_PRE_SECONDS", str(self._event_clip_seconds())) or str(self._event_clip_seconds()))
        except ValueError:
            value = self._event_clip_seconds()
        return min(max(value, 1.0), 30.0)

    def _event_post_seconds(self) -> float:
        try:
            value = float(os.environ.get("RECORDING_EVENT_POST_SECONDS", "3") or "3")
        except ValueError:
            value = 3.0
        return min(max(value, 0.0), 30.0)

    def _event_buffer_seconds(self) -> float:
        return min(self._event_pre_seconds() + self._event_post_seconds(), 60.0)

    def _event_clip_fps(self) -> float:
        try:
            value = float(os.environ.get("RECORDING_EVENT_CLIP_FPS", "6") or "6")
        except ValueError:
            value = 6.0
        return min(max(value, 1.0), 15.0)

    def _continuous_recording_enabled(self) -> bool:
        return os.environ.get("RECORDING_CONTINUOUS_ENABLED", "").strip().lower() in {"1", "true", "yes"}

    def _continuous_recording_enabled_for_camera(self, camera) -> bool:
        return self._continuous_recording_enabled() and bool(getattr(camera, "continuous_recording_enabled", True))

    @staticmethod
    def _parse_active_time(value: str):
        value = value.strip()
        if not value:
            return None
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError:
            return None

    def _continuous_recording_active_now(self, now: datetime | None = None) -> bool:
        start = self._parse_active_time(os.environ.get("RECORDING_CONTINUOUS_ACTIVE_START", ""))
        end = self._parse_active_time(os.environ.get("RECORDING_CONTINUOUS_ACTIVE_END", ""))
        if start is None or end is None or start == end:
            return True
        current = (now or datetime.now()).time()
        if start < end:
            return start <= current < end
        return current >= start or current < end

    def _continuous_segment_seconds(self) -> float:
        try:
            value = float(os.environ.get("RECORDING_CONTINUOUS_SEGMENT_SECONDS", "60") or "60")
        except ValueError:
            value = 60.0
        return min(max(value, 10.0), 900.0)

    def _continuous_recording_fps(self) -> float:
        try:
            value = float(os.environ.get("RECORDING_CONTINUOUS_FPS", "2") or "2")
        except ValueError:
            value = 2.0
        return min(max(value, 1.0), 10.0)

    def _append_recording_frame(self, camera_id: int, frame) -> None:
        now = time.monotonic()
        buffer = self._recording_buffers.setdefault(camera_id, deque())
        buffer.append((now, frame.copy()))
        cutoff = now - self._event_buffer_seconds()
        while buffer and buffer[0][0] < cutoff:
            buffer.popleft()

    def _recording_clip_frames(self, camera_id: int) -> list:
        cached = self._recording_buffers.get(camera_id)
        if not cached:
            return []
        cutoff = time.monotonic() - self._event_buffer_seconds()
        return [frame.copy() for timestamp, frame in cached if timestamp >= cutoff]

    def _handle_continuous_recording_frame(self, camera_id: int, frame, enabled_for_camera: bool = True) -> None:
        if not enabled_for_camera or not self._continuous_recording_active_now():
            self._continuous_recording_buffers.pop(camera_id, None)
            self._continuous_recording_started_at.pop(camera_id, None)
            self._last_continuous_recording_frame_at.pop(camera_id, None)
            return
        now = time.monotonic()
        fps = self._continuous_recording_fps()
        last_sampled_at = self._last_continuous_recording_frame_at.get(camera_id, 0.0)
        if now - last_sampled_at < (1.0 / fps):
            return
        self._last_continuous_recording_frame_at[camera_id] = now
        buffer = self._continuous_recording_buffers.setdefault(camera_id, deque())
        if camera_id not in self._continuous_recording_started_at:
            self._continuous_recording_started_at[camera_id] = now
        buffer.append((now, frame.copy()))
        if now - self._continuous_recording_started_at[camera_id] < self._continuous_segment_seconds():
            return
        frames = [item.copy() for _, item in buffer]
        buffer.clear()
        self._continuous_recording_started_at[camera_id] = now
        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(self._executor, lambda: self._save_continuous_recording_clip_sync(camera_id, frames))
        except RuntimeError:
            self._save_continuous_recording_clip_sync(camera_id, frames)

    def _save_event_recording_clip_sync(self, camera_id: int, alarm_id: int, frames: list, detection_payload: dict | None = None) -> None:
        if not frames:
            return
        storage_dir = recording_storage_dir() / f"cam_{camera_id}"
        storage_dir.mkdir(parents=True, exist_ok=True)
        created_at = utc_now()
        output_path = storage_dir / f"alarm_{alarm_id}_{created_at.strftime('%Y%m%d_%H%M%S')}.mp4"
        height, width = frames[0].shape[:2]
        fps = self._event_clip_fps()
        writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        if not writer.isOpened():
            logger.warning(f"[Recording] Kamera {camera_id} event clip yazici acilamadi: {output_path.name}")
            return
        written = 0
        try:
            for frame in frames:
                if frame.shape[:2] != (height, width):
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                writer.write(frame)
                written += 1
        finally:
            writer.release()
        if written == 0 or not output_path.exists():
            return
        metadata_path = self._write_event_detection_metadata(output_path, camera_id, alarm_id, detection_payload)
        db = self._open_db()
        try:
            repo = self._recording_repo(db)
            repo.add(RecordingSegment(
                id=None,
                camera_id=camera_id,
                started_at=created_at,
                ended_at=utc_now(),
                recording_type="event",
                status="complete",
                file_path=str(output_path),
                file_sha256=self._file_sha256(output_path),
                size_bytes=output_path.stat().st_size,
                codec="mp4v",
                width=width,
                height=height,
                fps=fps,
                alarm_id=alarm_id,
                created_at=created_at,
            ))
        finally:
            db.close()
        if metadata_path:
            logger.info("[Recording] Event clip detection metadata yazildi: %s", metadata_path.name)

    def _save_continuous_recording_clip_sync(self, camera_id: int, frames: list) -> None:
        if not frames:
            return
        storage_dir = recording_storage_dir() / f"cam_{camera_id}"
        storage_dir.mkdir(parents=True, exist_ok=True)
        created_at = utc_now()
        output_path = storage_dir / f"continuous_{created_at.strftime('%Y%m%d_%H%M%S')}.mp4"
        height, width = frames[0].shape[:2]
        fps = self._continuous_recording_fps()
        writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        if not writer.isOpened():
            logger.warning(f"[Recording] Kamera {camera_id} continuous clip yazici acilamadi: {output_path.name}")
            return
        written = 0
        try:
            for frame in frames:
                if frame.shape[:2] != (height, width):
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                writer.write(frame)
                written += 1
        finally:
            writer.release()
        if written == 0 or not output_path.exists():
            return
        duration_seconds = written / fps
        db = self._open_db()
        try:
            repo = self._recording_repo(db)
            repo.add(RecordingSegment(
                id=None,
                camera_id=camera_id,
                started_at=created_at,
                ended_at=utc_now(),
                recording_type="continuous",
                status="complete",
                file_path=str(output_path),
                file_sha256=self._file_sha256(output_path),
                size_bytes=output_path.stat().st_size,
                codec="mp4v",
                width=width,
                height=height,
                fps=fps,
                alarm_id=None,
                created_at=created_at,
            ))
            logger.info(
                "[Recording] Kamera %s continuous segment yazildi: %s frame, %.1f sn",
                camera_id,
                written,
                duration_seconds,
            )
        finally:
            db.close()

    def _write_event_detection_metadata(self, output_path, camera_id: int, alarm_id: int, detection_payload: dict | None):
        """Event clip yanina playback bbox metadata sidecar'i yazar."""
        if not detection_payload:
            return None
        metadata_path = output_path.with_suffix(".detections.json")
        payload = {
            "camera_id": camera_id,
            "alarm_id": alarm_id,
            "frame_width": detection_payload.get("frame_width"),
            "frame_height": detection_payload.get("frame_height"),
            "detected_at": detection_payload.get("detected_at"),
            "detections": detection_payload.get("detections") or [],
            "motion": detection_payload.get("motion"),
        }
        with open(metadata_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
        return metadata_path

    @staticmethod
    def _file_sha256(path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _mark_frame_broadcast(self, camera_id: int) -> None:
        """Son yayinlanan kare zamanlarini kisa pencere FPS hesabi icin tutar."""
        now = time.monotonic()
        samples = self._frame_broadcast_times.setdefault(camera_id, deque())
        samples.append(now)
        cutoff = now - 10.0
        while samples and samples[0] < cutoff:
            samples.popleft()

    def _current_broadcast_fps(self, camera_id: int) -> float | None:
        """Son 10 saniyelik yayin penceresinden efektif FPS degerini hesaplar."""
        samples = self._frame_broadcast_times.get(camera_id)
        if not samples or len(samples) < 2:
            return None
        elapsed = samples[-1] - samples[0]
        if elapsed <= 0:
            return None
        return (len(samples) - 1) / elapsed

    def _recent_detection_payload(self, camera_id: int) -> dict:
        """Son tespit kutularini kisa sure canli kare mesajlarina ekler."""
        cached = self._latest_detection_messages.get(camera_id)
        if not cached:
            return {
                "detections": [],
                "frame_width": None,
                "frame_height": None,
                "detected_at": None,
            }
        detected_at, payload = cached
        if time.monotonic() - detected_at > 5.0:
            self._latest_detection_messages.pop(camera_id, None)
            return {
                "detections": [],
                "frame_width": None,
                "frame_height": None,
                "detected_at": None,
            }
        return payload

    def _serialize_detection_result(self, result) -> dict:
        """Detection nesnelerini WebSocket JSON mesajina uygun hale getirir."""
        return {
            "detections": [
                {
                    "label": detection.label,
                    "confidence": detection.confidence,
                    "bounding_box": {
                        "x": detection.bounding_box.x,
                        "y": detection.bounding_box.y,
                        "width": detection.bounding_box.width,
                        "height": detection.bounding_box.height,
                    },
                }
                for detection in result.detections
            ],
            "frame_width": result.frame_width,
            "frame_height": result.frame_height,
            "detected_at": result.detected_at.isoformat() + "Z",
            "ai_inference_ms": result.inference_ms,
        }

    def _serialize_motion_result(self, result) -> dict:
        """Hareket alarmini WebSocket ve event metadata formatina cevirir."""
        return {
            "detections": [],
            "frame_width": result.frame_width,
            "frame_height": result.frame_height,
            "detected_at": result.detected_at.isoformat() + "Z",
            "ai_inference_ms": None,
            "motion": {
                "changed_ratio": result.motion_ratio,
                "changed_percent": round(result.motion_ratio * 100, 2),
            },
        }

    def _serialize_tamper_result(self, result: CameraTamperAnalysisResult) -> dict:
        """Kamera sabotaj analiz sonucunu WebSocket metadata formatina cevirir."""
        return {
            "detections": [],
            "frame_width": None,
            "frame_height": None,
            "detected_at": utc_now().isoformat() + "Z",
            "ai_inference_ms": None,
            "tamper": {
                "reason": result.reason,
                "brightness_mean": round(result.brightness_mean, 2),
                "brightness_stddev": round(result.brightness_stddev, 2),
                "blur_variance": round(result.blur_variance, 2),
            },
        }

    def _record_person_analytics_sync(self, camera_id: int, detection_payload: dict) -> None:
        """AI insan tespiti sonucunu saatlik kamera yogunlugu istatistigine ekler."""
        detections = detection_payload.get("detections") or []
        if not detections or not self._db_session_factory or not self._person_analytics_repository_factory:
            return
        detected_at_raw = detection_payload.get("detected_at")
        try:
            detected_at = datetime.fromisoformat(str(detected_at_raw).replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            detected_at = utc_now()
        confidences = [
            float(item.get("confidence"))
            for item in detections
            if isinstance(item, dict) and item.get("confidence") is not None
        ]
        db = self._db_session_factory()
        try:
            repo = self._person_analytics_repository_factory(db)
            current_bucket = repo.record_detection(
                camera_id=camera_id,
                detected_at=detected_at,
                person_count=len(detections),
                max_confidence=max(confidences) if confidences else None,
            )
            self._maybe_create_person_density_alarm_sync(db, repo, camera_id, current_bucket)
            retention_days = int(os.environ.get("PERSON_ANALYTICS_RETENTION_DAYS", "90") or "90")
            repo.prune_older_than(min(max(retention_days, 1), 3650))
        except Exception as exc:
            logger.debug("[PersonAnalytics] Kamera %s istatistik yazimi basarisiz: %s", camera_id, exc)
        finally:
            db.close()

    def _maybe_create_person_density_alarm_sync(self, db, analytics_repo, camera_id: int, current_bucket) -> None:
        """Saatlik insan yogunlugu beklenenin uzerindeyse ek guvenlik alarmi uretir."""
        if not self._alarm_repository_factory or not self._person_density_policy.enabled:
            return
        now_value = utc_now()
        alarm_type = AlarmType.PERSON_DENSITY_ANOMALY
        camera_alarm_times = self._last_alarm_times.setdefault(camera_id, {})
        last_alarm_at = camera_alarm_times.get((camera_id, alarm_type))
        if last_alarm_at and now_value - last_alarm_at < timedelta(seconds=self._person_density_policy.alarm_cooldown_seconds):
            return

        since = current_bucket.hour_start - timedelta(hours=self._person_density_policy.baseline_window_hours)
        until = current_bucket.hour_start - timedelta(seconds=1)
        previous = analytics_repo.list_hourly(
            camera_id,
            since,
            until,
            limit=self._person_density_policy.baseline_window_hours,
        )
        result = self._person_density_policy.evaluate(current_bucket, previous)
        if not result.triggered:
            return

        alarm_repo = self._alarm_repo(db)
        open_alarm = alarm_repo.get_latest_open(camera_id, alarm_type)
        if open_alarm is not None:
            camera_alarm_times[(camera_id, alarm_type)] = now_value
            return

        baseline_text = "-"
        if result.baseline_peak_average is not None:
            baseline_text = f"{result.baseline_peak_average:.1f}"
        alarm_repo.add(Alarm(
            id=None,
            camera_id=camera_id,
            alarm_type=alarm_type,
            status=AlarmStatus.NEW,
            confidence=min(max(result.score, 0.0), 1.0),
            bounding_box=None,
            snapshot_path=None,
            snapshot_sha256=None,
            snapshot_annotated_path=None,
            snapshot_annotated_sha256=None,
            message=(
                "Olagan disi insan yogunlugu: "
                f"bu saatte tepe kisi sayisi {current_bucket.max_person_count}, "
                f"toplam sayim {current_bucket.total_person_count}, "
                f"gecmis saat ortalamasi {baseline_text}."
            ),
            severity=AlarmSeverity.HIGH,
            created_at=now_value,
        ))
        camera_alarm_times[(camera_id, alarm_type)] = now_value

    def _file_sha256(self, filepath: str) -> str:
        with open(filepath, "rb") as file:
            return hashlib.sha256(file.read()).hexdigest()

    def _save_tamper_snapshot(self, frame: object, camera_id: int) -> tuple[str | None, str | None]:
        snapshot_dir = os.environ.get("SNAPSHOT_DIR", "snapshots") or "snapshots"
        os.makedirs(snapshot_dir, exist_ok=True)
        path = os.path.join(snapshot_dir, f"cam_{camera_id}_{utc_now().strftime('%Y%m%d_%H%M%S')}_tamper.jpg")
        if not cv2.imwrite(path, frame):
            return None, None
        return path, self._file_sha256(path)

    def _detect_tamper_and_alarm_sync(self, camera_id: int, frame) -> tuple[Alarm | None, CameraTamperAnalysisResult | None]:
        """Goruntu karartma/kapama/bulaniklastirma sinyalinden sabotaj alarmi uretir."""
        if not self._db_session_factory or not self._alarm_repository_factory:
            return None, None

        result = self._camera_tamper_policy.analyze(frame)
        if not result.triggered:
            self._tamper_suspicious_counts[camera_id] = 0
            return None, result

        suspicious_count = self._tamper_suspicious_counts.get(camera_id, 0) + 1
        self._tamper_suspicious_counts[camera_id] = suspicious_count
        if suspicious_count < self._camera_tamper_policy.consecutive_frames:
            return None, result

        now_value = utc_now()
        alarm_type = AlarmType.CAMERA_TAMPERED
        camera_alarm_times = self._last_alarm_times.setdefault(camera_id, {})
        last_alarm_at = camera_alarm_times.get((camera_id, alarm_type))
        if last_alarm_at and now_value - last_alarm_at < timedelta(seconds=self._camera_tamper_policy.alarm_cooldown_seconds):
            return None, result

        db = self._db_session_factory()
        try:
            camera_repo = self._camera_repo(db)
            camera = camera_repo.get_by_id(camera_id)
            if not camera or camera.status != CameraStatus.ACTIVE:
                return None, result
            alarm_repo = self._alarm_repo(db)
            open_alarm = alarm_repo.get_latest_open(camera_id, alarm_type)
            if open_alarm is not None:
                camera_alarm_times[(camera_id, alarm_type)] = now_value
                return open_alarm, result

            snapshot_path, snapshot_sha256 = self._save_tamper_snapshot(frame, camera_id)
            alarm = Alarm(
                id=None,
                camera_id=camera_id,
                alarm_type=alarm_type,
                status=AlarmStatus.NEW,
                confidence=min(max(result.score, 0.0), 1.0),
                bounding_box=None,
                snapshot_path=snapshot_path,
                snapshot_sha256=snapshot_sha256,
                snapshot_annotated_path=None,
                snapshot_annotated_sha256=None,
                severity=AlarmSeverity.HIGH,
                message=(
                    "Kamera sabotaj supheli: "
                    f"{result.reason}; parlaklik {result.brightness_mean:.1f}, "
                    f"duzlugu {result.brightness_stddev:.1f}, bulaniklik {result.blur_variance:.1f}."
                ),
                created_at=now_value,
            )
            saved_alarm = alarm_repo.add(alarm)
            camera_alarm_times[(camera_id, alarm_type)] = now_value
            return saved_alarm, result
        finally:
            db.close()

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

    def _sync_get_state(self, camera_id: int) -> Optional[Tuple[CameraStatus, bool, bool, bool]]:
        db = self._open_db()
        try:
            repo = self._camera_repo(db)
            cam = repo.get_by_id(camera_id)
            if not cam:
                return None
            return cam.status, cam.ai_detection_enabled, cam.motion_detection_enabled, self._continuous_recording_enabled_for_camera(cam)
        finally:
            db.close()

    def _sync_check_ai_enabled_cached(self, camera_id: int) -> bool:
        """Son işlenen kare sırasında öğrenilen AI durumunu döner (ekstra DB sorgusu yok)."""
        return self._ai_enabled_cache.get(camera_id, False)

    def _sync_check_motion_enabled_cached(self, camera_id: int) -> bool:
        """Son islenen kare sirasinda ogrenilen hareket algilama durumunu doner."""
        return self._motion_enabled_cache.get(camera_id, False)

    def get_runtime_telemetry(self, camera_id: int) -> dict:
        """Canlı akış üreticisinin çalışma durumunu özetler."""
        cached = self._latest_messages.get(camera_id)
        last_broadcast_at = cached[0] if cached else None
        now = time.monotonic()
        producer_task = self._producers.get(camera_id)
        ai_task = self._active_ai_tasks.get(camera_id)
        motion_task = self._active_motion_tasks.get(camera_id)
        tamper_task = self._active_tamper_tasks.get(camera_id)
        subscriber_count = len(self._subscribers.get(camera_id, ()))
        producer_started_at_monotonic = self._producer_started_at_monotonic.get(camera_id)
        return {
            "producer_running": bool(producer_task and not producer_task.done()),
            "producer_started_at": self._producer_started_at.get(camera_id),
            "producer_uptime_seconds": (now - producer_started_at_monotonic) if producer_started_at_monotonic else None,
            "producer_start_count": self._producer_start_counts.get(camera_id, 0),
            "subscriber_count": subscriber_count,
            "active_profile": self._effective_profile_name(camera_id),
            "current_broadcast_fps": self._current_broadcast_fps(camera_id),
            "ai_task_running": bool(ai_task and not ai_task.done()),
            "motion_task_running": bool(motion_task and not motion_task.done()),
            "tamper_task_running": bool(tamper_task and not tamper_task.done()),
            "ai_provider": getattr(self._ai_service, "active_provider", None),
            "ai_frame_stride": self._ai_frame_stride_cache.get(camera_id, 1),
            "last_ai_inference_ms": self._last_ai_inference_ms.get(camera_id),
            "average_ai_inference_ms": self._avg_ai_inference_ms.get(camera_id),
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
                return None, False, False, False, 1, False

            self._ai_enabled_cache[camera_id] = camera.ai_detection_enabled
            self._motion_enabled_cache[camera_id] = camera.motion_detection_enabled
            self._ai_frame_stride_cache[camera_id] = max(1, getattr(camera, "ai_frame_stride", 1) or 1)
            continuous_recording_enabled = self._continuous_recording_enabled_for_camera(camera)

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
                return None, True, camera.ai_detection_enabled, camera.motion_detection_enabled, self._ai_frame_stride_cache[camera_id], continuous_recording_enabled

            return frame, True, camera.ai_detection_enabled, camera.motion_detection_enabled, self._ai_frame_stride_cache[camera_id], continuous_recording_enabled
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
            result = use_case.analyze_and_alarm(camera_id, frame, camera=camera)
            self._last_alarm_times[camera_id] = dict(use_case._last_alarms)
            return result
        finally:
            db.close()

    def _detect_motion_and_alarm_sync(self, camera_id: int, previous_frame, current_frame) -> Optional[object]:
        """Onceden okunmus iki kare uzerinde hareket tespiti ve alarm uretimi yapar."""
        from src.application.use_cases.frame_processing_use_case import ProcessFrameUseCase

        db = self._open_db()
        try:
            camera_repo = self._camera_repo(db)
            alarm_repo = self._alarm_repo(db)
            camera = camera_repo.get_by_id(camera_id)
            if not camera or not camera.motion_detection_enabled or camera.status != CameraStatus.ACTIVE:
                return None

            use_case = ProcessFrameUseCase(
                camera_repository=camera_repo,
                alarm_repository=alarm_repo,
                frame_source=None,
                ai_service=self._ai_service,
                cooldown_seconds=self._cooldown_seconds,
            )
            use_case._last_alarms = dict(self._last_alarm_times.get(camera_id, {}))
            result = use_case.analyze_motion_and_alarm(camera_id, previous_frame, current_frame, camera=camera)
            self._last_alarm_times[camera_id] = dict(use_case._last_alarms)
            return result
        finally:
            db.close()
