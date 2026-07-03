"""
WebSocket canlı akış endpoint'i.

GET /api/streams/{camera_id}?token=<jwt>

Kamera başına TEK bir arka plan üretici (CameraStreamManager) RTSP'den kare
okur ve bağlı tüm istemcilere (aynı ağdaki farklı cihazlar dahil) yayınlar.
Bu sayede kaç istemci aynı kamerayı izlerse izlesin, sadece TEK RTSP bağlantısı
açılır ve canlı izleme görüntü hızı AI'nın tespit hızına bağlı kalmaz.
"""
import os

# FFMPEG timeout — cv2 yüklenmeden ÖNCE set edilmeli (bkz. opencv_stream_reader.py)
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "timeout;5000000|stimeout;5000000|rw_timeout;5000000|rtsp_transport;tcp",
)

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/streams", tags=["Streams"])
logger = logging.getLogger(__name__)

PROFILE_SEND_INTERVALS = {
    "grid": 0.25,      # 4 FPS: çoklu kamera ekranı için ağ/tarayıcı yükünü düşürür
    "live": 1 / 15,    # 15 FPS: tam ekran izleme için akıcı profil
    "alarm": 0.5,      # 2 FPS: alarm önizleme kartları için yeterli
}


async def _reject(websocket: WebSocket, msg: str) -> None:
    """Bağlantıyı mesajla kapat — double-close hatasını yakala."""
    try:
        await websocket.send_json({"error": msg})
    except Exception:
        pass
    try:
        await websocket.close(code=4005)
    except RuntimeError:
        pass   # "send once close sent" — zaten kapanıyor


async def force_disconnect(camera_id: int, reason: str = "Kamera izlemesi durduruldu.") -> None:
    """Bir kameraya ait tüm açık izleme bağlantılarını anında kapatır.

    Admin kamerayı "İzlemeyi Durdur" veya sil dediğinde çağrılır — periyodik
    durum kontrolünü beklemeden istemcileri haberdar eder.
    """
    from src.presentation.api.dependencies import stream_manager
    await stream_manager.close_all(camera_id, reason)


@router.websocket("/{camera_id}")
async def stream_camera(websocket: WebSocket, camera_id: int, token: str = None, profile: str = "grid"):
    """
    Kameranın canlı görüntüsünü WebSocket ile binary JPEG olarak iletir.
    Kamera pasif, silinmiş veya erişilemez hâle gelince bağlantı kapatılır.
    """
    await websocket.accept()

    # JWT doğrulama
    if not token:
        await _reject(websocket, "Authentication token required")
        return
    try:
        from src.infrastructure.security.jwt_service import decode_access_token
        decode_access_token(token)
    except Exception:
        await _reject(websocket, "Invalid or expired token")
        return

    from src.presentation.api.dependencies import stream_manager

    queue = await stream_manager.subscribe(camera_id, profile=profile)
    if queue is None:
        logger.info(f"[Streams] Kamera {camera_id} aktif değil — bağlantı reddedildi.")
        await _reject(websocket, "Kamera aktif değil veya bulunamadı.")
        return

    send_interval = PROFILE_SEND_INTERVALS.get(profile, PROFILE_SEND_INTERVALS["grid"])
    last_frame_sent = 0.0

    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                # Uzun süre kare gelmedi (örn. kamera erişilemiyor) — bağlantı
                # canlı tutulur, istemci tarafı zaten durumu gösterir.
                continue

            if message.get("closed"):
                await _reject(websocket, message.get("reason", "Bağlantı kapatıldı."))
                return

            frame = message.get("frame")
            now = asyncio.get_running_loop().time()
            should_send_frame = frame is not None and now - last_frame_sent >= send_interval

            if should_send_frame or message.get("alarm_triggered"):
                await websocket.send_json({
                    "alarm_triggered": bool(message.get("alarm_triggered")),
                    "alarm_id": message.get("alarm_id"),
                })

            if should_send_frame:
                if isinstance(frame, (bytes, bytearray, memoryview)):
                    await websocket.send_bytes(bytes(frame))
                else:
                    # Geriye dönük uyumluluk: eski Base64 mesajı gelirse JSON olarak ilet.
                    await websocket.send_json(message)
                last_frame_sent = now
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(f"[Streams] Kamera {camera_id} akış hatası: {exc}")
    finally:
        stream_manager.unsubscribe(camera_id, queue)
