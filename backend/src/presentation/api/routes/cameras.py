"""
Kamera yönetimi endpoint'leri.

POST   /cameras/                  — yeni kamera ekler
GET    /cameras/                  — tüm kameraları listeler
GET    /cameras/{id}              — tekil kamera detayı
GET    /cameras/{id}/stream-token — kısa ömürlü canlı akış token'ı üretir
DELETE /cameras/{id}              — kamera siler, akış yöneticisini durdurur
PATCH  /cameras/{id}/status       — ACTIVE/INACTIVE değiştirir, akış yöneticisi buna göre güncellenir
PATCH  /cameras/{id}/ai           — AI insan tespitini açar/kapatır, akış yöneticisi buna göre güncellenir
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from typing import List
from urllib.parse import unquote, urlparse
from src.presentation.api.dependencies import get_camera_use_cases, get_stream_manager, get_current_user, get_operator_user, frame_source
from src.application.use_cases.camera_use_cases import CameraUseCases
from src.application.services.camera_stream_manager import CameraStreamManager
from src.presentation.api.schemas.camera_schema import (
    CameraCreate,
    CameraUpdate,
    CameraResponse,
    CameraScanRequest,
    CameraScanResult,
    CameraStreamDiagnostics,
)
from src.domain.entities.camera import CameraStatus
from src.infrastructure.camera.camera_scanner import (
    build_candidate_ports,
    check_port_async,
    check_rtsp_path_async,
    find_working_rtsp_path_async,
    scan_cameras_async,
    validate_rtsp_endpoint_variants_async,
)
from src.infrastructure.security.jwt_service import create_stream_token

router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.post("/", response_model=CameraResponse, status_code=201)
async def add_camera(
    camera_data: CameraCreate,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_operator_user),
):
    """Sisteme yeni bir kamera ekler."""
    try:
        rtsp_port = camera_data.rtsp_port or 554
        rtsp_path = camera_data.rtsp_path or ""
        host = camera_data.host
        username = camera_data.username
        password = camera_data.password
        brand = camera_data.brand
        model = camera_data.model

        if rtsp_path.lower().startswith("rtsp://"):
            parsed = urlparse(rtsp_path)
            host = parsed.hostname or host
            rtsp_port = parsed.port or rtsp_port
            username = unquote(parsed.username) if parsed.username else username
            password = unquote(parsed.password) if parsed.password else password
            rtsp_path = parsed.path or ""
            if parsed.query:
                rtsp_path = f"{rtsp_path}?{parsed.query}"

        if not rtsp_path:
            detected = await asyncio.wait_for(
                find_working_rtsp_path_async(
                    host,
                    rtsp_port,
                    username or "",
                    password or "",
                    camera_data.auto_rtsp_ports,
                ),
                timeout=45.0 if camera_data.auto_rtsp_ports else 20.0,
            )
            if not detected:
                raise ValueError(
                    "Kamera RTSP akışı doğrulanamadı. RTSP Path alanını cihazın gerçek akış yolu ile girin "
                    "(ör. Illustra için /videoStreamId=1, /stream1 veya i610 için 7778 portunda /primarystream)."
                )
            rtsp_path = detected["path"]
            rtsp_port = detected["port"]
            brand = brand or detected.get("brand")
        else:
            is_reachable = False
            for candidate_port in build_candidate_ports(rtsp_port, camera_data.auto_rtsp_ports):
                try:
                    is_reachable = await asyncio.wait_for(
                        check_rtsp_path_async(
                            host,
                            candidate_port,
                            rtsp_path,
                            username or "",
                            password or "",
                        ),
                        timeout=12.0,
                    )
                except asyncio.TimeoutError:
                    is_reachable = False
                if is_reachable:
                    rtsp_port = candidate_port
                    break
            if not is_reachable:
                raise ValueError(
                    "Kamera RTSP akışı doğrulanamadı. IP, port, RTSP path ve kullanıcı/şifre bilgisini kontrol edin."
                )

        camera = use_cases.add_camera(
            name=camera_data.name,
            host=host,
            rtsp_path=rtsp_path,
            rtsp_port=rtsp_port,
            onvif_port=camera_data.onvif_port or 80,
            username=username,
            encrypted_password=password,
            brand=brand,
            model=model,
        )
        # RTSP doğrulaması başarılıysa kamerayı hemen aktif et ve akışı başlat
        camera = use_cases.update_camera_status(camera.id, CameraStatus.ACTIVE)
        await sm.ensure_running_state(camera.id)
        return camera
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Kamera RTSP doğrulaması zaman aşımına uğradı. Port ve path bilgisini kontrol edin; i610 için genelde 7778 portu ve /primarystream kullanılır.",
        )


@router.get("/", response_model=List[CameraResponse])
def list_cameras(
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    current_user: dict = Depends(get_current_user),
):
    """Sistemdeki tüm kameraları listeler."""
    return use_cases.list_cameras()


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(
    camera_id: int,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    current_user: dict = Depends(get_current_user),
):
    """Belirli bir kameranın detaylarını getirir."""
    camera = use_cases.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera bulunamadı")
    return camera


@router.get("/{camera_id}/stream-token")
def create_camera_stream_token(
    camera_id: int,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    current_user: dict = Depends(get_current_user),
):
    """Belirli kamera için kısa ömürlü WebSocket izleme token'ı üretir."""
    camera = use_cases.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera bulunamadı.")
    token = create_stream_token(
        username=current_user.get("sub", ""),
        role=current_user.get("role", ""),
        camera_id=camera_id,
    )
    return {"stream_token": token, "expires_in": 60}


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    data: CameraUpdate,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_operator_user),
):
    """Kameranın adını, host'unu, port ve path gibi bağlantı bilgilerini günceller."""
    camera = use_cases.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera bulunamadı")

    # Bağlantı bilgilerinin değişip değişmediğini kontrol et
    connection_changed = False
    if data.host is not None and data.host != camera.host:
        connection_changed = True
    if data.rtsp_port is not None and data.rtsp_port != camera.rtsp_port:
        connection_changed = True
    if data.rtsp_path is not None and data.rtsp_path != camera.rtsp_path:
        connection_changed = True
    if data.username is not None and data.username != camera.username:
        connection_changed = True
    if data.password is not None:
        connection_changed = True

    if data.name is not None:
        camera.name = data.name
    if data.host is not None:
        camera.host = data.host
    if data.rtsp_port is not None:
        camera.rtsp_port = data.rtsp_port
    if data.rtsp_path is not None:
        camera.rtsp_path = data.rtsp_path
    if data.onvif_port is not None:
        camera.onvif_port = data.onvif_port
    if data.username is not None:
        camera.username = data.username
    if data.password is not None:
        camera.encrypted_password = use_cases._encrypt_password(data.password)

    updated_camera = use_cases.update_camera(camera)

    # Bağlantı ayarları değiştiyse yayını sıfırla ve yeniden bağlandır
    if connection_changed:
        await sm.reset_stream(camera_id)

    return updated_camera


@router.get("/{camera_id}/diagnostics/rtsp")
async def diagnose_camera_rtsp(
    camera_id: int,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    current_user: dict = Depends(get_operator_user),
):
    """Kayıtlı kameranın RTSP erişimini şifre göstermeden test eder."""
    camera = use_cases.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera bulunamadı")

    password = camera.encrypted_password or ""
    if password:
        try:
            from src.presentation.api.dependencies import password_service
            password = password_service.decrypt(password)
        except Exception:
            pass

    path = camera.rtsp_path or ""
    public_path = path if path.startswith("/") else f"/{path}"
    public_url = f"rtsp://{camera.host}:{camera.rtsp_port}{public_path}"
    masked_auth = f"{camera.username}:****@" if camera.username else ""
    masked_url = f"rtsp://{masked_auth}{camera.host}:{camera.rtsp_port}{public_path}"

    tcp_open = await check_port_async(camera.host, camera.rtsp_port, timeout=2.0)
    describe_ok = await check_rtsp_path_async(
        camera.host,
        camera.rtsp_port,
        path,
        camera.username or "",
        password,
        timeout=2.0,
    )
    frame_result = await validate_rtsp_endpoint_variants_async(
        camera.host,
        camera.rtsp_port,
        path,
        camera.username or "",
        password,
    )
    authenticated_frame_ok = frame_result["authenticated"]
    anonymous_frame_ok = frame_result["anonymous"]
    frame_ok = authenticated_frame_ok or anonymous_frame_ok

    if frame_ok:
        if anonymous_frame_ok and not authenticated_frame_ok and camera.username:
            message = "RTSP anonim erişimle frame veriyor; kayıtlı kullanıcı/şifreli URL frame vermiyor."
        else:
            message = "RTSP bağlantısı doğrulandı; gerçek frame okunabiliyor."
    elif describe_ok:
        if camera.nvr_id:
            message = "RTSP DESCRIBE başarılı, ancak frame okunamadı. NVR kanal path'ini, kanal yetkisini ve NVR üzerindeki canlı görüntüyü kontrol edin."
        else:
            message = "RTSP DESCRIBE başarılı, ancak frame okunamadı. Kamera stream profilini, codec'i ve RTSP transport ayarını kontrol edin."
    elif tcp_open:
        message = "Port açık, ancak RTSP path veya kullanıcı/şifre doğrulanamadı."
    else:
        message = "RTSP portuna TCP bağlantısı kurulamadı."

    return {
        "camera_id": camera.id,
        "name": camera.name,
        "host": camera.host,
        "rtsp_port": camera.rtsp_port,
        "rtsp_path": path,
        "nvr_id": camera.nvr_id,
        "has_username": bool(camera.username),
        "public_url": public_url,
        "authenticated_url_masked": masked_url,
        "tcp_open": tcp_open,
        "describe_ok": describe_ok,
        "frame_ok": frame_ok,
        "authenticated_frame_ok": authenticated_frame_ok,
        "anonymous_frame_ok": anonymous_frame_ok,
        "message": message,
    }


@router.get("/{camera_id}/diagnostics/stream", response_model=CameraStreamDiagnostics)
async def diagnose_camera_stream(
    camera_id: int,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_operator_user),
):
    """Kayıtlı kameranın canlı akış ve üretici sağlık metriklerini döner."""
    camera = use_cases.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera bulunamadı")

    frame_stats = frame_source.get_camera_telemetry(camera)
    runtime_stats = sm.get_runtime_telemetry(camera_id)

    return {
        "camera_id": camera_id,
        "producer_running": runtime_stats["producer_running"],
        "subscriber_count": runtime_stats["subscriber_count"],
        "active_profile": runtime_stats["active_profile"],
        "ai_task_running": runtime_stats["ai_task_running"],
        "cached_frame_available": runtime_stats["cached_frame_available"],
        "last_broadcast_age_seconds": runtime_stats["last_broadcast_age_seconds"],
        "last_frame_age_seconds": frame_stats["last_frame_age_seconds"],
        "open_attempts": frame_stats["open_attempts"],
        "open_failures": frame_stats["open_failures"],
        "failure_count": frame_stats["failure_count"],
        "retry_cooldown_seconds": frame_stats["retry_cooldown_seconds"],
        "warmup_reads": frame_stats["warmup_reads"],
        "open_timeout_ms": frame_stats["open_timeout_ms"],
        "read_timeout_ms": frame_stats["read_timeout_ms"],
        "last_success_at": frame_stats["last_success_at"],
        "last_failure_at": frame_stats["last_failure_at"],
        "last_broadcast_at": frame_stats["last_success_at"],
    }


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: int,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_operator_user),
):
    """Belirli bir kamerayı sistemden siler."""
    await sm.close_all(camera_id, "Kamera silindi.")
    use_cases.delete_camera(camera_id)


@router.patch("/{camera_id}/status", response_model=CameraResponse)
async def update_camera_status(
    camera_id: int,
    status: CameraStatus,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_operator_user),
):
    """Kameranın aktif/pasif durumunu günceller; akış yöneticisini buna göre günceller."""
    try:
        camera = use_cases.update_camera_status(camera_id, status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # İzleme durduruldu/pasife alındıysa açık canlı yayın bağlantılarını anında kapat —
    # admin "İzlemeyi Durdur" dediğinde periyodik kontrolü (saniyeler sürer) beklememeli
    if camera.status != CameraStatus.ACTIVE:
        await sm.close_all(camera_id, "Kamera izlemesi durduruldu.")
    else:
        await sm.ensure_running_state(camera_id)

    return camera


@router.patch("/{camera_id}/ai", response_model=CameraResponse)
async def update_camera_ai(
    camera_id: int,
    enabled: bool,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_operator_user),
):
    """AI insan tespitini açar veya kapatır.

    Kamera ACTIVE iken AI açılırsa arka plan üretici başlar (izleyici olmasa
    da); kapatılırsa ve hiç izleyici yoksa üretici durur. Kamera INACTIVE
    iken değişiklik yalnızca DB'ye kaydedilir.
    """
    try:
        camera = use_cases.update_camera_ai_detection(camera_id, enabled)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if camera.status == CameraStatus.ACTIVE:
        await sm.ensure_running_state(camera_id)

    return camera


@router.post("/scan", response_model=List[CameraScanResult])
async def scan_cameras(
    scan_data: CameraScanRequest,
    request: Request,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    current_user: dict = Depends(get_operator_user),
):
    """Ağdaki kameraları tarar. İstemci bağlantıyı keser veya 'Durdur' basarsa tarama iptal edilir."""
    timeout = 180.0 if scan_data.auto_rtsp_ports else 120.0
    scan_task = asyncio.create_task(
        scan_cameras_async(
            ip_range=scan_data.ip_range,
            rtsp_port=scan_data.rtsp_port or 554,
            username=scan_data.username or "",
            password=scan_data.password or "",
            auto_ports=scan_data.auto_rtsp_ports,
        )
    )
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    try:
        while not scan_task.done():
            if await request.is_disconnected():
                scan_task.cancel()
                try:
                    await scan_task
                except (asyncio.CancelledError, Exception):
                    pass
                return []
            remaining = deadline - loop.time()
            if remaining <= 0:
                scan_task.cancel()
                raise HTTPException(
                    status_code=504,
                    detail="Kamera taraması zaman aşımına uğradı. Daha küçük bir IP aralığı deneyin veya i610 için RTSP portunu 7778 yapın.",
                )
            await asyncio.sleep(min(0.5, remaining))
        return await scan_task
    except asyncio.CancelledError:
        scan_task.cancel()
        return []
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/bulk-add", response_model=List[CameraResponse])
async def bulk_add_cameras(
    cameras: List[CameraCreate],
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_operator_user),
):
    """Birden fazla kamerayı toplu olarak sisteme ekler."""
    try:
        cameras_dicts = [cam.dict() for cam in cameras]
        added = use_cases.bulk_add_cameras(cameras_dicts)
        # Tarama ile eklenen kameralar RTSP doğrulamasından geçti — hemen aktif et
        result = []
        for camera in added:
            activated = use_cases.update_camera_status(camera.id, CameraStatus.ACTIVE)
            await sm.ensure_running_state(activated.id)
            result.append(activated)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
