"""
NVR (Network Video Recorder) yönetimi endpoint'leri.

POST   /nvrs/               — yeni NVR ekler
GET    /nvrs/               — tüm NVR'ları listeler
GET    /nvrs/{id}           — tekil NVR detayı
PATCH  /nvrs/{id}           — NVR bilgilerini günceller
DELETE /nvrs/{id}           — NVR siler (bağlı kameralar nvr_id=null olur)
POST   /nvrs/{id}/probe     — ONVIF ile kanalları önizler, kaydetmez
POST   /nvrs/{id}/import    — ONVIF kanallarını kamera olarak içe aktarır
"""
import logging
import asyncio
import re
from urllib.parse import urlsplit, urlunsplit
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List

from src.presentation.api.dependencies import (
    get_nvr_use_cases,
    get_camera_use_cases,
    get_nvr_probe_service,
    get_stream_manager,
    get_current_user,
    get_operator_user,
)
from src.application.use_cases.nvr_use_cases import NVRUseCases
from src.application.use_cases.camera_use_cases import CameraUseCases
from src.application.services.camera_stream_manager import CameraStreamManager
from src.domain.entities.camera import CameraStatus
from src.presentation.api.schemas.nvr_schema import (
    NVRCreate,
    NVRPageResponse,
    NVRUpdate,
    NVRResponse,
    NVRChannelInfo,
    NVRDiscoverResponse,
    NVRImportRequest,
    NVRProbeDiagnostics,
    NVRScanRequest,
    NVRScanResponse,
)
from src.presentation.api.schemas.camera_schema import CameraResponse
from src.infrastructure.security.audit_logger import write_audit_event

logger = logging.getLogger(__name__)


def mask_rtsp_url(rtsp_url: str) -> str:
    """RTSP URL içindeki şifreyi log için maskeler."""
    try:
        parsed = urlsplit(rtsp_url)
        if parsed.username is None:
            return rtsp_url
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        netloc = f"{parsed.username}:***@{host}{port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    except Exception:
        return "rtsp://***"


def infer_channel_number(endpoint: dict, profile_name: str = "", profile_token: str = "") -> int | None:
    """RTSP path, profil adı veya token içinden NVR kanal numarasını tahmin eder."""
    text = " ".join([endpoint.get("path") or "", profile_name or "", profile_token or ""])

    for pattern in [
        r"/media/(\d+)/",
        r"[?&]channel=(\d+)",
        r"/ch(?:annel)?[_-]?(\d+)",
        r"Channels/(\d+)0[12]",
        r"(?:kanal|channel|ch)[ _-]*(\d+)",
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if "Channels/" in pattern and value > 100:
                return value // 100
            return value
    return None


def build_nvr_channel_candidates(endpoint: dict, nvr, username: str, password: str, channel: int | None) -> list[dict]:
    """ONVIF URL çalışmazsa denenecek NVR host/port/path adaylarını üretir.

    Öncelik sırası:
    1. NVR host + ONVIF path/port  — ONVIF iç IP döndürdüğünde hızla doğru adrese ulaşır
    2. ONVIF URL (orijinal host)   — iç IP olmayan durumlarda da çalışır
    3. NVR host + alternatif portlar ve kanal path'leri
    """
    onvif_host = endpoint.get("host") or nvr.host
    onvif_port = endpoint["port"]
    onvif_path = endpoint.get("path") or ""

    base_ports = [onvif_port, 554, 7778, 8554]
    base_paths = [onvif_path] if onvif_path else []

    if channel:
        base_paths.extend([
            f"/media/{channel}/video/1",
            f"/media/{channel}/video/0",
            f"/media/{channel}/video/2",
            f"/Streaming/Channels/{channel}01",
            f"/Streaming/Channels/{channel}02",
            f"/cam/realmonitor?channel={channel}&subtype=0",
            f"/cam/realmonitor?channel={channel}&subtype=1",
            f"/live/ch{channel}",
            f"/ch{channel}",
        ])

    raw_candidates = []

    def _add(host: str, port: int, path: str, source: str) -> None:
        if path:
            raw_candidates.append({
                "host": host, "port": port, "path": path,
                "username": username, "password": password, "source": source,
            })

    # 1. NVR hostu + ONVIF path — ONVIF iç IP döndürdüğünde zaman kaybetmeden
    #    doğru adrese gitmeyi sağlar (Hikvision, Dahua, Annke iç IP sorunu)
    if onvif_path and onvif_host != nvr.host:
        _add(nvr.host, onvif_port, onvif_path, "NVR host (ONVIF path)")
        if onvif_port != 554:
            _add(nvr.host, 554, onvif_path, "NVR host port-554 (ONVIF path)")

    # 2. ONVIF'in döndürdüğü orijinal URL
    if onvif_path:
        _add(onvif_host, onvif_port, onvif_path, "ONVIF URL")

    # 3. NVR hostu + alternatif port ve path kombinasyonları
    for port in base_ports:
        for path in base_paths:
            _add(nvr.host, port, path, "NVR alternatif")

    seen: set[tuple[str, int, str]] = set()
    candidates = []
    for c in raw_candidates:
        key = (c["host"], c["port"], c["path"])
        if key not in seen:
            seen.add(key)
            candidates.append(c)
    return candidates[:16]


async def resolve_reachable_rtsp_endpoint(
    endpoint: dict,
    nvr,
    username: str,
    password: str,
    profile_name: str = "",
    profile_token: str = "",
) -> dict:
    """
    NVR kanal URL'si kaydedilmeden önce erişilebilen host/port/path kombinasyonunu seçer.
    Bazı NVR'lar ONVIF'te kameranın iç IP'sini döndürür; sunucu bu IP'ye ulaşamıyorsa aynı RTSP path NVR host'u ile denenir.

    Yalnızca gerçek kare okunabilen endpoint döndürülür. DESCRIBE tek başına
    oynatılabilir video kanıtı değildir.
    """
    from src.infrastructure.camera.camera_scanner import check_rtsp_path_async, validate_rtsp_endpoint_variants_async

    path = endpoint.get("path") or ""
    if not path:
        raise ValueError("NVR kanalının RTSP path bilgisi boş.")

    channel = infer_channel_number(endpoint, profile_name, profile_token)
    candidates = build_nvr_channel_candidates(endpoint, nvr, username, password, channel)
    tested: list[str] = []

    logger.info(f"[NVR Import] Kanal={channel or '?'} — {len(candidates)} aday test ediliyor")

    for i, candidate in enumerate(candidates, 1):
        label = f"{candidate['host']}:{candidate['port']}{candidate['path']}"
        logger.info(f"[NVR Import] Aday {i}/{len(candidates)} → {label}")
        try:
            # frame_fallback=False: OpenCV fallback yok, sadece TCP DESCRIBE/auth kontrolü.
            # Timeout 6s: yavaş NVR'larda Digest el sıkışması için yeterli.
            describe_ok = await asyncio.wait_for(
                check_rtsp_path_async(
                    candidate["host"],
                    candidate["port"],
                    candidate["path"],
                    candidate["username"] or "",
                    candidate["password"] or "",
                    frame_fallback=False,
                ),
                timeout=6.0,
            )
        except asyncio.TimeoutError:
            describe_ok = False
        if not describe_ok:
            logger.debug(f"[NVR Import]   DESCRIBE=YOK → {label}")
            tested.append(f"{label} (DESCRIBE=YOK)")
            continue

        logger.info(f"[NVR Import]   DESCRIBE=OK → {label} — frame doğrulaması başlıyor (max 12s)")
        frame_result = await validate_rtsp_endpoint_variants_async(
            candidate["host"],
            candidate["port"],
            candidate["path"],
            candidate["username"] or "",
            candidate["password"] or "",
            timeout=12.0,
        )

        frame_ok = bool(frame_result["authenticated"] or frame_result["anonymous"])
        tested.append(
            f"{label} (DESCRIBE=OK, "
            f"AUTH_FRAME={'OK' if frame_result['authenticated'] else 'YOK'}, "
            f"ANON_FRAME={'OK' if frame_result['anonymous'] else 'YOK'})"
        )
        if frame_ok:
            logger.info(f"[NVR Import]   Frame doğrulama BAŞARILI → {label}")
            return candidate
        logger.warning(f"[NVR Import]   Frame doğrulama başarısız (DESCRIBE=OK) → {label}")

    # Hiç DESCRIBE=OK yok → doğrudan frame dene (son çare, NVR DESCRIBE gerektirmeyebilir)
    if candidates:
        fallback = candidates[0]
        label = f"{fallback['host']}:{fallback['port']}{fallback['path']}"
        logger.warning(f"[NVR Import] Tüm DESCRIBE=YOK → doğrudan frame deneniyor: {label}")
        try:
            frame_result = await asyncio.wait_for(
                validate_rtsp_endpoint_variants_async(
                    fallback["host"], fallback["port"], fallback["path"],
                    fallback["username"] or "", fallback["password"] or "",
                    timeout=12.0,
                ),
                timeout=14.0,
            )
        except asyncio.TimeoutError:
            frame_result = {"authenticated": False, "anonymous": False}
        if frame_result["authenticated"] or frame_result["anonymous"]:
            logger.info(f"[NVR Import] Doğrudan frame başarılı → {label}")
            return fallback

    tested_text = "; ".join(tested[:12])
    raise ValueError(
        f"NVR kanalından gerçek frame okunamadı. Kanal={channel or 'bilinmiyor'}. Denenen adaylar: {tested_text}"
    )


async def get_nvr_channels_hybrid(nvr, plain_pass, probe_svc) -> List[NVRChannelInfo]:
    # 1. ONVIF üzerinden dene
    try:
        channels = probe_svc.get_stream_uris(
            host=nvr.host,
            onvif_port=nvr.onvif_port,
            username=nvr.username or "",
            password=plain_pass,
        )
        if channels:
            return [
                NVRChannelInfo(
                    profile_token=ch.profile_token,
                    profile_name=ch.profile_name,
                    manufacturer=ch.manufacturer,
                    model=ch.model,
                    rtsp_url=ch.rtsp_url,
                )
                for ch in channels
            ]
    except Exception as exc:
        logger.warning(f"NVR ONVIF probe failed for {nvr.host}, falling back to RTSP scan: {exc}")

    # 2. RTSP Tarama Fallback'i
    from src.infrastructure.camera.camera_scanner import scan_nvr_channels_async
    rtsp_channels = await scan_nvr_channels_async(
        host=nvr.host,
        rtsp_port=554,
        username=nvr.username or "",
        password=plain_pass,
    )
    return [
        NVRChannelInfo(
            profile_token=ch["profile_token"],
            profile_name=ch["profile_name"],
            manufacturer=ch["manufacturer"],
            model=ch["model"],
            rtsp_url=ch["rtsp_url"],
        )
        for ch in rtsp_channels
    ]

async def get_nvr_channels_hybrid(nvr, plain_pass, probe_svc) -> List[NVRChannelInfo]:
    diagnostics = await get_nvr_probe_diagnostics(nvr, plain_pass, probe_svc)
    return diagnostics.channels


async def get_nvr_probe_diagnostics(nvr, plain_pass, probe_svc) -> NVRProbeDiagnostics:
    onvif_error = None
    fallback_error = None

    try:
        channels = probe_svc.get_stream_uris(
            host=nvr.host,
            onvif_port=nvr.onvif_port,
            username=nvr.username or "",
            password=plain_pass,
        )
        if channels:
            channel_infos = [
                NVRChannelInfo(
                    profile_token=ch.profile_token,
                    profile_name=ch.profile_name,
                    manufacturer=ch.manufacturer,
                    model=ch.model,
                    rtsp_url=ch.rtsp_url,
                    source="onvif",
                    diagnostic="ONVIF GetProfiles/GetStreamUri başarılı.",
                )
                for ch in channels
            ]
            return NVRProbeDiagnostics(
                source="onvif",
                onvif_ok=True,
                fallback_used=False,
                device_manufacturer=channel_infos[0].manufacturer,
                device_model=channel_infos[0].model,
                profile_count=len(channel_infos),
                stream_uri_count=len(channel_infos),
                channels=channel_infos,
            )
        onvif_error = "ONVIF bağlantısı başarılı olabilir ancak stream profili/URI dönmedi."
    except Exception as exc:
        onvif_error = str(exc)
        logger.warning(f"NVR ONVIF probe failed for {nvr.host}, falling back to RTSP scan: {exc}")

    from src.infrastructure.camera.camera_scanner import scan_nvr_channels_async
    try:
        rtsp_channels = await scan_nvr_channels_async(
            host=nvr.host,
            rtsp_port=554,
            username=nvr.username or "",
            password=plain_pass,
        )
        channel_infos = [
            NVRChannelInfo(
                profile_token=ch["profile_token"],
                profile_name=ch["profile_name"],
                manufacturer=ch["manufacturer"],
                model=ch["model"],
                rtsp_url=ch["rtsp_url"],
                source="rtsp_fallback",
                diagnostic=f"ONVIF başarısız: {onvif_error}",
            )
            for ch in rtsp_channels
        ]
    except Exception as exc:
        fallback_error = str(exc)
        channel_infos = []

    return NVRProbeDiagnostics(
        source="rtsp_fallback" if channel_infos else "none",
        onvif_ok=False,
        fallback_used=True,
        profile_count=0,
        stream_uri_count=0,
        onvif_error=onvif_error,
        fallback_error=fallback_error,
        channels=channel_infos,
    )


router = APIRouter(prefix="/nvrs", tags=["NVR Cihazları"])


@router.post("/", response_model=NVRResponse, status_code=201)
def add_nvr(
    data: NVRCreate,
    request: Request,
    use_cases: NVRUseCases = Depends(get_nvr_use_cases),
    current_user: dict = Depends(get_operator_user),
):
    """Sisteme yeni bir NVR cihazı ekler."""
    try:
        nvr = use_cases.add_nvr(
            name=data.name,
            host=data.host,
            onvif_port=data.onvif_port,
            username=data.username,
            password=data.password,
            brand=data.brand,
            model=data.model,
        )
        write_audit_event(
            "nvr.create",
            actor=current_user.get("sub"),
            source_ip=request.client.host if request.client else None,
            metadata={"nvr_id": nvr.id, "host": nvr.host},
        )
        return nvr
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[NVRResponse] | NVRPageResponse)
def list_nvrs(
    paginated: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    search: str = "",
    status: str = "all",
    sort: str = "name_asc",
    use_cases: NVRUseCases = Depends(get_nvr_use_cases),
    current_user: dict = Depends(get_current_user),
):
    """Kayitli NVR cihazlarini listeler; paginated=true ise sayfali yanit dondurur."""
    if paginated:
        items, total = use_cases.list_nvrs_paginated(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            sort=sort,
        )
        return {"items": items, "total": total, "page": page, "page_size": page_size}
    return use_cases.list_nvrs()


@router.get("/{nvr_id}", response_model=NVRResponse)
def get_nvr(
    nvr_id: int,
    use_cases: NVRUseCases = Depends(get_nvr_use_cases),
    current_user: dict = Depends(get_current_user),
):
    """Belirli bir NVR cihazının detaylarını getirir."""
    nvr = use_cases.get_nvr(nvr_id)
    if not nvr:
        raise HTTPException(status_code=404, detail="NVR bulunamadı.")
    return nvr


@router.patch("/{nvr_id}", response_model=NVRResponse)
def update_nvr(
    nvr_id: int,
    data: NVRUpdate,
    request: Request,
    use_cases: NVRUseCases = Depends(get_nvr_use_cases),
    current_user: dict = Depends(get_operator_user),
):
    """NVR cihazının adını, host'unu, portunu veya kimlik bilgilerini günceller."""
    nvr = use_cases.get_nvr(nvr_id)
    if not nvr:
        raise HTTPException(status_code=404, detail="NVR bulunamadı.")

    if data.name is not None:
        nvr.name = data.name
    if data.host is not None:
        nvr.host = data.host
    if data.onvif_port is not None:
        nvr.onvif_port = data.onvif_port
    if data.username is not None:
        nvr.username = data.username
    updated = use_cases.update_nvr(nvr, plain_password=data.password if data.password is not None else None)
    write_audit_event(
        "nvr.update",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"nvr_id": nvr_id},
    )
    return updated


@router.patch("/{nvr_id}/status", response_model=NVRResponse)
def update_nvr_status(
    nvr_id: int,
    is_active: bool,
    request: Request,
    use_cases: NVRUseCases = Depends(get_nvr_use_cases),
    current_user: dict = Depends(get_operator_user),
):
    """NVR cihazını aktif veya pasif yapar."""
    nvr = use_cases.get_nvr(nvr_id)
    if not nvr:
        raise HTTPException(status_code=404, detail="NVR bulunamadı.")
    nvr.is_active = is_active
    updated = use_cases.update_nvr(nvr)
    write_audit_event(
        "nvr.status",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"nvr_id": nvr_id, "is_active": is_active},
    )
    return updated


@router.delete("/{nvr_id}", status_code=204)
def delete_nvr(
    nvr_id: int,
    request: Request,
    use_cases: NVRUseCases = Depends(get_nvr_use_cases),
    current_user: dict = Depends(get_operator_user),
):
    """Belirli bir NVR cihazını siler (bağlı kameralar nvr_id=null olur)."""
    use_cases.delete_nvr(nvr_id)
    write_audit_event(
        "nvr.delete",
        actor=current_user.get("sub"),
        source_ip=request.client.host if request.client else None,
        metadata={"nvr_id": nvr_id},
    )


@router.post("/{nvr_id}/probe", response_model=List[NVRChannelInfo])
async def probe_nvr_channels(
    nvr_id: int,
    nvr_use_cases: NVRUseCases = Depends(get_nvr_use_cases),
    probe_svc=Depends(get_nvr_probe_service),
    current_user: dict = Depends(get_operator_user),
):
    """
    NVR'a ONVIF veya RTSP kanalları tarayarak bağlanır ve bağlı kamera kanallarını listeler.
    Kameraları sisteme KAYDETMEZ — yalnızca önizleme sağlar.
    """
    nvr = nvr_use_cases.get_nvr(nvr_id)
    if not nvr:
        raise HTTPException(status_code=404, detail="NVR bulunamadı.")

    from src.presentation.api.dependencies import password_service
    plain_pass = ""
    if nvr.encrypted_password:
        try:
            plain_pass = password_service.decrypt(nvr.encrypted_password)
        except Exception:
            plain_pass = nvr.encrypted_password

    try:
        channels = await get_nvr_channels_hybrid(nvr, plain_pass, probe_svc)
        return channels
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/{nvr_id}/probe/diagnostics", response_model=NVRProbeDiagnostics)
async def probe_nvr_channels_diagnostics(
    nvr_id: int,
    nvr_use_cases: NVRUseCases = Depends(get_nvr_use_cases),
    probe_svc=Depends(get_nvr_probe_service),
    current_user: dict = Depends(get_operator_user),
):
    """NVR kanal keşfini ONVIF/fallback teşhis bilgisiyle döner."""
    nvr = nvr_use_cases.get_nvr(nvr_id)
    if not nvr:
        raise HTTPException(status_code=404, detail="NVR bulunamadı.")

    from src.presentation.api.dependencies import password_service
    plain_pass = ""
    if nvr.encrypted_password:
        try:
            plain_pass = password_service.decrypt(nvr.encrypted_password)
        except Exception:
            plain_pass = nvr.encrypted_password

    return await get_nvr_probe_diagnostics(nvr, plain_pass, probe_svc)


@router.post("/{nvr_id}/import", response_model=List[CameraResponse], status_code=201)
async def import_nvr_cameras(
    nvr_id: int,
    body: NVRImportRequest,
    request: Request,
    nvr_use_cases: NVRUseCases = Depends(get_nvr_use_cases),
    cam_use_cases: CameraUseCases = Depends(get_camera_use_cases),
    probe_svc=Depends(get_nvr_probe_service),
    sm: CameraStreamManager = Depends(get_stream_manager),
    current_user: dict = Depends(get_operator_user),
):
    """
    NVR'dan keşfedilen kanalları doğrudan sisteme kamera olarak kaydeder.
    Süreçte tekrar ağ taraması yapılmaz, veriler anında kaydedilir.
    """
    nvr = nvr_use_cases.get_nvr(nvr_id)
    if not nvr:
        raise HTTPException(status_code=404, detail="NVR bulunamadı.")

    from src.presentation.api.dependencies import password_service
    plain_pass = ""
    if nvr.encrypted_password:
        try:
            plain_pass = password_service.decrypt(nvr.encrypted_password)
        except Exception:
            plain_pass = nvr.encrypted_password

    try:
        imported: list = []
        logger.info(f"[NVR Import] NVR={nvr.host} — {len(body.channels)} kanal aktarılacak")
        for idx, ch in enumerate(body.channels, 1):
            logger.info(
                f"[NVR Import] Kanal {idx}/{len(body.channels)}: {ch.profile_name} — "
                f"{mask_rtsp_url(ch.rtsp_url)}"
            )
            endpoint = probe_svc.parse_rtsp_endpoint(ch.rtsp_url, nvr.host)
            logger.debug(f"[NVR Import]   Parse sonucu: host={endpoint.get('host')} port={endpoint.get('port')} path={endpoint.get('path')}")
            camera_username = endpoint["username"] if endpoint["username"] is not None else nvr.username
            camera_password = endpoint["password"] if endpoint["password"] is not None else plain_pass
            reachable_endpoint = await resolve_reachable_rtsp_endpoint(
                endpoint,
                nvr,
                camera_username or "",
                camera_password or "",
                ch.profile_name,
                ch.profile_token,
            )
            logger.info(
                f"[NVR Import]   Endpoint seçildi: {reachable_endpoint['host']}:{reachable_endpoint['port']}"
                f"{reachable_endpoint['path']} → ACTIVE (frame doğrulandı)"
            )
            camera = cam_use_cases.add_camera(
                name=f"{nvr.name} — {ch.profile_name}",
                host=reachable_endpoint["host"],
                rtsp_path=reachable_endpoint["path"],
                rtsp_port=reachable_endpoint["port"],
                onvif_port=nvr.onvif_port,
                username=camera_username,
                encrypted_password=camera_password,
                nvr_id=nvr_id,
                brand=ch.manufacturer,
                model=ch.model,
            )
            camera = cam_use_cases.update_camera_status(camera.id, CameraStatus.ACTIVE)
            await sm.ensure_running_state(camera.id)
            imported.append(camera)

        logger.info(f"[NVR Import] Tamamlandı — {len(imported)} kamera aktarıldı")
        write_audit_event(
            "nvr.import",
            actor=current_user.get("sub"),
            source_ip=request.client.host if request.client else None,
            metadata={"nvr_id": nvr_id, "count": len(imported)},
        )
        return imported
    except Exception as e:
        logger.error(f"[NVR Import] Hata: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/discover", response_model=List[NVRDiscoverResponse])
async def discover_nvrs(
    current_user: dict = Depends(get_operator_user),
):
    """
    WS-Discovery (Web Services Dynamic Discovery) kullanarak yerel ağdaki ONVIF/NVR cihazlarını arar.
    """
    import asyncio
    from urllib.parse import urlparse
    from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
    from wsdiscovery import Scope

    def run_discovery():
        wsd = WSDiscovery()
        wsd.start()
        scope = Scope("onvif://www.onvif.org/Profile")
        services = wsd.searchServices(scopes=[scope])
        devices = []
        for service in services:
            xaddrs = service.getXAddrs()
            if xaddrs:
                xaddr = xaddrs[0]
                try:
                    parsed = urlparse(xaddr)
                    host = parsed.hostname or ""
                    port = parsed.port or 80
                    # Zaten eklenmiş olanları filtrelemek veya sadece listelemek için IP ve Port'u dönüyoruz
                    devices.append({
                        "xaddr": xaddr,
                        "host": host,
                        "port": port
                    })
                except Exception:
                    pass
        wsd.stop()
        return devices

    # Event loop'u tıkamamak için ThreadPoolExecutor'da çalıştırıyoruz (run_in_executor)
    loop = asyncio.get_running_loop()
    discovered_devices = await loop.run_in_executor(None, run_discovery)
    return discovered_devices


@router.post("/scan", response_model=List[NVRScanResponse])
async def scan_nvrs(
    scan_data: NVRScanRequest,
    request: Request,
    current_user: dict = Depends(get_operator_user),
):
    """Ağda NVR (VideoEdge, Hikvision, Dahua) cihazlarını IP aralığına göre tarar. İstemci 'Durdur' basarsa iptal edilir."""
    from src.infrastructure.camera.camera_scanner import scan_nvrs_async
    scan_task = asyncio.create_task(
        scan_nvrs_async(
            ip_range=scan_data.ip_range,
            rtsp_port=scan_data.rtsp_port or 554,
            username=scan_data.username or "",
            password=scan_data.password or "",
        )
    )
    loop = asyncio.get_event_loop()
    deadline = loop.time() + 120.0
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
                raise HTTPException(status_code=504, detail="NVR taraması zaman aşımına uğradı. Daha küçük bir IP aralığı deneyin.")
            await asyncio.sleep(min(0.5, remaining))
        return await scan_task
    except asyncio.CancelledError:
        scan_task.cancel()
        return []
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk-add", response_model=List[NVRResponse], status_code=201)
def bulk_add_nvrs(
    nvrs: List[NVRCreate],
    request: Request,
    use_cases: NVRUseCases = Depends(get_nvr_use_cases),
    current_user: dict = Depends(get_operator_user),
):
    """Birden fazla NVR cihazını toplu olarak sisteme ekler."""
    try:
        if len(nvrs) > 100:
            raise HTTPException(status_code=413, detail="Tek seferde en fazla 100 NVR eklenebilir.")
        nvrs_dicts = [nvr.dict() for nvr in nvrs]
        added = use_cases.bulk_add_nvrs(nvrs_dicts)
        write_audit_event(
            "nvr.bulk_add",
            actor=current_user.get("sub"),
            source_ip=request.client.host if request.client else None,
            metadata={"count": len(added)},
        )
        return added
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
