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
from src.presentation.api.dependencies import (
    get_camera_health_repository,
    get_camera_use_cases,
    get_stream_manager,
    get_current_user,
    get_operator_user,
    frame_source,
)
from src.application.use_cases.camera_use_cases import CameraUseCases
from src.application.services.camera_stream_manager import CameraStreamManager
from src.presentation.api.schemas.camera_schema import (
    CameraCreate,
    CameraUpdate,
    CameraResponse,
    CameraScanRequest,
    CameraScanResult,
    CameraRtspDiagnostics,
    CameraRtspPreviewRequest,
    CameraHealthSummaryResponse,
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
from src.infrastructure.security.audit_logger import write_audit_event

router = APIRouter(prefix="/cameras", tags=["Cameras"])


def _normalize_rtsp_fields(
    host: str,
    rtsp_port: int,
    rtsp_path: str,
    username: str,
    password: str,
) -> tuple[str, int, str, str, str]:
    """Tam RTSP URL girildiyse host/port/path/auth alanlarina ayirir."""
    path = rtsp_path or ""
    if path.lower().startswith("rtsp://"):
        parsed = urlparse(path)
        host = parsed.hostname or host
        rtsp_port = parsed.port or rtsp_port
        username = unquote(parsed.username) if parsed.username else username
        password = unquote(parsed.password) if parsed.password else password
        path = parsed.path or ""
        if parsed.query:
            path = f"{path}?{parsed.query}"
    return host, rtsp_port, path, username, password


async def _build_rtsp_diagnostics(
    *,
    camera_id: int,
    name: str,
    host: str,
    rtsp_port: int,
    rtsp_path: str,
    username: str,
    password: str,
    nvr_id: int | None = None,
) -> dict:
    """RTSP TCP/DESCRIBE/frame testlerini ortak sonuc semasina donusturur."""
    host, rtsp_port, path, username, password = _normalize_rtsp_fields(
        host,
        rtsp_port,
        rtsp_path,
        username,
        password,
    )
    public_path = path if path.startswith("/") else f"/{path}"
    public_url = f"rtsp://{host}:{rtsp_port}{public_path}"
    masked_auth = f"{username}:****@" if username else ""
    masked_url = f"rtsp://{masked_auth}{host}:{rtsp_port}{public_path}"

    tcp_open = await check_port_async(host, rtsp_port, timeout=2.0)
    describe_ok = await check_rtsp_path_async(
        host,
        rtsp_port,
        path,
        username,
        password,
        timeout=2.0,
    )
    frame_result = await validate_rtsp_endpoint_variants_async(
        host,
        rtsp_port,
        path,
        username,
        password,
    )
    authenticated_frame_ok = frame_result["authenticated"]
    anonymous_frame_ok = frame_result["anonymous"]
    frame_ok = authenticated_frame_ok or anonymous_frame_ok

    if frame_ok:
        if anonymous_frame_ok and not authenticated_frame_ok and username:
            message = "RTSP anonim erisimle frame veriyor; kullanici/sifreli URL frame vermiyor."
        else:
            message = "RTSP baglantisi dogrulandi; gercek frame okunabiliyor."
    elif describe_ok:
        if nvr_id:
            message = "RTSP DESCRIBE basarili, ancak frame okunamadi. NVR kanal path'ini, kanal yetkisini ve NVR uzerindeki canli goruntuyu kontrol edin."
        else:
            message = "RTSP DESCRIBE basarili, ancak frame okunamadi. Kamera stream profilini, codec'i ve RTSP transport ayarini kontrol edin."
    elif tcp_open:
        message = "Port acik, ancak RTSP path veya kullanici/sifre dogrulanamadi."
    else:
        message = "RTSP portuna TCP baglantisi kurulamadi."

    return {
        "camera_id": camera_id,
        "name": name,
        "host": host,
        "rtsp_port": rtsp_port,
        "rtsp_path": path,
        "nvr_id": nvr_id,
        "has_username": bool(username),
        "public_url": public_url,
        "authenticated_url_masked": masked_url,
        "tcp_open": tcp_open,
        "describe_ok": describe_ok,
        "frame_ok": frame_ok,
        "authenticated_frame_ok": authenticated_frame_ok,
        "anonymous_frame_ok": anonymous_frame_ok,
        "message": message,
    }


@router.post("/", response_model=CameraResponse, status_code=201)
async def add_camera(
    camera_data: CameraCreate,
    request: Request,
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
            ai_confidence_threshold=camera_data.ai_confidence_threshold,
            ai_iou_threshold=camera_data.ai_iou_threshold,
            ai_alarm_cooldown_seconds=camera_data.ai_alarm_cooldown_seconds,
            ai_frame_stride=camera_data.ai_frame_stride,
            ai_inference_width=camera_data.ai_inference_width,
            ai_active_start=camera_data.ai_active_start,
            ai_active_end=camera_data.ai_active_end,
            ai_roi_polygon=camera_data.ai_roi_polygon,
        )
        # RTSP doğrulaması başarılıysa kamerayı hemen aktif et ve akışı başlat
        camera = use_cases.update_camera_status(camera.id, CameraStatus.ACTIVE)
        await sm.ensure_running_state(camera.id)
        write_audit_event(
            "camera.create",
            actor=current_user.get("sub"),
            source_ip=request.client.host if request.client else None,
            metadata={"camera_id": camera.id, "host": camera.host},
        )
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


@router.post("/diagnostics/rtsp-preview", response_model=CameraRtspDiagnostics)
async def preview_camera_rtsp(
    data: CameraRtspPreviewRequest,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    current_user: dict = Depends(get_operator_user),
):
    """Kaydetmeden formdaki RTSP alanlariyla baglanti testi yapar."""
    camera = use_cases.get_camera(data.camera_id) if data.camera_id else None
    if data.camera_id and not camera:
        raise HTTPException(status_code=404, detail="Kamera bulunamadi")

    host = data.host or (camera.host if camera else "")
    if not host:
        raise HTTPException(status_code=400, detail="Host bilgisi gereklidir.")

    password = data.password
    if password is None and camera:
        password = camera.encrypted_password or ""
        if password:
            try:
                from src.presentation.api.dependencies import password_service
                password = password_service.decrypt(password)
            except Exception:
                pass

    return await _build_rtsp_diagnostics(
        camera_id=camera.id if camera else 0,
        name=data.name or (camera.name if camera else "Kaydedilmemis kamera"),
        host=host,
        rtsp_port=data.rtsp_port or (camera.rtsp_port if camera else 554),
        rtsp_path=data.rtsp_path if data.rtsp_path is not None else (camera.rtsp_path if camera else ""),
        username=data.username if data.username is not None else (camera.username if camera else "") or "",
        password=password or "",
        nvr_id=camera.nvr_id if camera else None,
    )


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
    request: Request,
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
    ai_settings_changed = False
    if data.ai_confidence_threshold is not None:
        camera.ai_confidence_threshold = data.ai_confidence_threshold
        ai_settings_changed = True
    if data.ai_iou_threshold is not None:
        camera.ai_iou_threshold = data.ai_iou_threshold
        ai_settings_changed = True
    if data.ai_alarm_cooldown_seconds is not None:
        camera.ai_alarm_cooldown_seconds = data.ai_alarm_cooldown_seconds
        ai_settings_changed = True
    if data.ai_frame_stride is not None:
        camera.ai_frame_stride = data.ai_frame_stride
        ai_settings_changed = True
    if data.ai_inference_width is not None:
        camera.ai_inference_width = data.ai_inference_width
        ai_settings_changed = True
    if data.ai_active_start is not None:
        camera.ai_active_start = data.ai_active_start
        ai_settings_changed = True
    if data.ai_active_end is not None:
        camera.ai_active_end = data.ai_active_end
        ai_settings_changed = True
    if data.ai_roi_polygon is not None:
        camera.ai_roi_polygon = data.ai_roi_polygon
        ai_settings_changed = True
    updated_camera = use_cases.update_camera(camera, plain_password=data.password if data.password is not None else None)

    # Bağlantı ayarları değiştiyse yayını sıfırla ve yeniden bağlandır
    if connection_changed:
        await sm.reset_stream(camera_id)
    elif ai_settings_changed:
        await sm.ensure_running_state(camera_id)

    write_audit_event(
        "camera.update",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"camera_id": camera_id, "connection_changed": connection_changed, "ai_settings_changed": ai_settings_changed},
    )
    return updated_camera


@router.get("/{camera_id}/diagnostics/rtsp", response_model=CameraRtspDiagnostics)
async def diagnose_camera_rtsp(
    camera_id: int,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    current_user: dict = Depends(get_operator_user),
):
    """Kayitli kameranin RTSP erisimini sifre gostermeden test eder."""
    camera = use_cases.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera bulunamadi")

    password = camera.encrypted_password or ""
    if password:
        try:
            from src.presentation.api.dependencies import password_service
            password = password_service.decrypt(password)
        except Exception:
            pass

    return await _build_rtsp_diagnostics(
        camera_id=camera.id,
        name=camera.name,
        host=camera.host,
        rtsp_port=camera.rtsp_port,
        rtsp_path=camera.rtsp_path or "",
        username=camera.username or "",
        password=password,
        nvr_id=camera.nvr_id,
    )


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
        "ai_provider": runtime_stats["ai_provider"],
        "ai_frame_stride": camera.ai_frame_stride,
        "ai_inference_width": camera.ai_inference_width,
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


@router.get("/{camera_id}/diagnostics/health-history", response_model=CameraHealthSummaryResponse)
async def diagnose_camera_health_history(
    camera_id: int,
    limit: int = 120,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    health_repo=Depends(get_camera_health_repository),
    current_user: dict = Depends(get_operator_user),
):
    """Kayitli kameranin son erisilebilirlik olcumlerini ve trend ozetini dondurur."""
    camera = use_cases.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera bulunamadi")

    safe_limit = min(max(limit, 1), 500)
    samples = list(health_repo.list_recent(camera_id, safe_limit))
    reachable_count = sum(1 for sample in samples if sample.reachable)
    unreachable_count = len(samples) - reachable_count
    latest = samples[0] if samples else None

    return {
        "camera_id": camera_id,
        "sample_count": len(samples),
        "reachable_count": reachable_count,
        "unreachable_count": unreachable_count,
        "availability_percent": round((reachable_count / len(samples)) * 100, 1) if samples else None,
        "latest_checked_at": latest.checked_at if latest else None,
        "latest_latency_ms": latest.latency_ms if latest else None,
        "latest_failure_reason": latest.failure_reason if latest else None,
        "samples": samples,
    }


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: int,
    request: Request,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_operator_user),
):
    """Belirli bir kamerayı sistemden siler."""
    await sm.close_all(camera_id, "Kamera silindi.")
    use_cases.delete_camera(camera_id)
    write_audit_event(
        "camera.delete",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"camera_id": camera_id},
    )


@router.patch("/{camera_id}/status", response_model=CameraResponse)
async def update_camera_status(
    camera_id: int,
    status: CameraStatus,
    request: Request,
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

    write_audit_event(
        "camera.status",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"camera_id": camera_id, "status": status.value},
    )
    return camera


@router.patch("/{camera_id}/ai", response_model=CameraResponse)
async def update_camera_ai(
    camera_id: int,
    enabled: bool,
    request: Request,
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

    write_audit_event(
        "camera.ai",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"camera_id": camera_id, "enabled": enabled},
    )
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
    request: Request,
    use_cases: CameraUseCases = Depends(get_camera_use_cases),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_operator_user),
):
    """Birden fazla kamerayı toplu olarak sisteme ekler."""
    try:
        if len(cameras) > 100:
            raise HTTPException(status_code=413, detail="Tek seferde en fazla 100 kamera eklenebilir.")
        cameras_dicts = [cam.dict() for cam in cameras]
        added = use_cases.bulk_add_cameras(cameras_dicts)
        # Tarama ile eklenen kameralar RTSP doğrulamasından geçti — hemen aktif et
        result = []
        for camera in added:
            activated = use_cases.update_camera_status(camera.id, CameraStatus.ACTIVE)
            await sm.ensure_running_state(activated.id)
            result.append(activated)
        write_audit_event(
            "camera.bulk_add",
            actor=current_user.get("sub"),
            source_ip=request.client.host if request.client else None,
            metadata={"count": len(result)},
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
