import asyncio
import ipaddress
import json
import logging
import os
import re
import base64
import hashlib
from urllib.parse import quote
from typing import List, Dict, Any

# OPENCV_FFMPEG_CAPTURE_OPTIONS main.py'de process başlangıcında set edildi.
# Bu modül o değeri DEĞİŞTİRMEZ — thread-safety için.
import cv2

logger = logging.getLogger(__name__)

_PATHS_JSON_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "rtsp_paths.json")
)
COMMON_RTSP_PORTS = [554, 8554, 10554, 7070, 7777, 7778]


def build_candidate_ports(preferred_port: int = 554, include_common: bool = False) -> List[int]:
    """Seçili portu ilk sıraya alarak denenebilir RTSP port listesini üretir."""
    ports = [preferred_port or 554]
    if include_common:
        ports.extend(COMMON_RTSP_PORTS)
    seen = set()
    return [port for port in ports if port and not (port in seen or seen.add(port))]

def load_rtsp_paths() -> List[Dict[str, str]]:
    """rtsp_paths.json dosyasından ortak akış yollarını yükler."""
    if not os.path.exists(_PATHS_JSON_PATH):
        return [
            { "path": "/stream1", "brand": "Generic/Illustra", "desc": "Main stream" },
            { "path": "/videoStreamId=1", "brand": "American Dynamics", "desc": "Illustra main stream" }
        ]
    try:
        with open(_PATHS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def build_rtsp_url(ip: str, port: int, path: str, username: str = "", password: str = "") -> str:
    """RTSP URL'sini kullanıcı adı/şifreyi güvenli encode ederek oluşturur.

    RFC 3986 sub-delimiter karakterler (! $ & ' ( ) * + , ; =) şifrede encode edilmez.
    FFmpeg URL'i parse ederken bu karakterleri decode etmez, Digest hash yanlış olur.
    """
    _PWD_SAFE = "!$&'()*+,;="
    auth = ""
    if username:
        auth = f"{quote(username, safe='')}:{quote(password or '', safe=_PWD_SAFE)}@"
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"rtsp://{auth}{ip}:{port}{normalized_path}"

def validate_rtsp_url_sync(rtsp_url: str) -> bool:
    """OpenCV/FFmpeg ile gerçek kare okunabildiğini doğrular.

    OPENCV_FFMPEG_CAPTURE_OPTIONS (TCP + stimeout) main.py'de set edildiği için
    burada env var değiştirilmiyor — thread-safety korunur.
    """
    from src.infrastructure.camera.opencv_stream_reader import _mask_url
    masked = _mask_url(rtsp_url)
    cap = cv2.VideoCapture()
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5_000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3_000)
    try:
        cap.open(rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            logger.debug(f"[Scanner] VideoCapture açılamadı → {masked}")
            return False
        ok, frame = cap.read()
        if ok and frame is not None:
            h, w = frame.shape[:2] if frame is not None else (0, 0)
            logger.info(f"[Scanner] Frame doğrulama BAŞARILI {w}x{h} → {masked}")
            return True
        logger.debug(f"[Scanner] Cap açıldı ama frame okunamadı → {masked}")
        return False
    finally:
        cap.release()

async def validate_rtsp_endpoint_async(
    ip: str, port: int, path: str, username: str = "", password: str = ""
) -> bool:
    """RTSP endpoint'inden gerçek frame okunabildiğini thread içinde test eder."""
    result = await validate_rtsp_endpoint_variants_async(ip, port, path, username, password)
    return bool(result["authenticated"] or result["anonymous"])


async def validate_rtsp_endpoint_variants_async(
    ip: str, port: int, path: str, username: str = "", password: str = "",
    timeout: float = 10.0,
) -> Dict[str, bool]:
    """Kimlik bilgili ve anonim RTSP frame okuma denemelerini ayrı ayrı döner.

    timeout: validate_rtsp_url_sync OPEN(5s)+READ(3s)=8s olduğundan varsayılan 10s.
    """
    rtsp_url = build_rtsp_url(ip, port, path, username, password)
    authenticated = False
    try:
        authenticated = await asyncio.wait_for(
            asyncio.to_thread(validate_rtsp_url_sync, rtsp_url),
            timeout=timeout,
        )
    except Exception:
        authenticated = False

    anonymous = False
    if username:
        anonymous_url = build_rtsp_url(ip, port, path, "", "")
        try:
            anonymous = await asyncio.wait_for(
                asyncio.to_thread(validate_rtsp_url_sync, anonymous_url),
                timeout=timeout,
            )
        except Exception:
            anonymous = False

    return {"authenticated": authenticated, "anonymous": anonymous}

def parse_ip_range(ip_range: str) -> List[str]:
    """
    IP aralığını çözümleyerek tekil IP listesi döner.
    Desteklenen formatlar:
      - CIDR: 192.168.1.0/24
      - Tire (Hyphen): 192.168.1.50-100 veya 192.168.1.50-192.168.1.100
      - Virgülle ayrılmış liste: 192.168.1.50, 192.168.1.51
    Maksimum 256 IP ile sınırlandırılmıştır.
    """
    ip_range = ip_range.strip()
    # CIDR
    if "/" in ip_range:
        try:
            net = ipaddress.ip_network(ip_range, strict=False)
            ips = [str(ip) for ip in net.hosts()]
            return ips[:256]
        except ValueError:
            pass

    # Tire (Tireli aralık)
    if "-" in ip_range:
        parts = ip_range.split("-")
        if len(parts) == 2:
            start_str = parts[0].strip()
            end_str = parts[1].strip()
            try:
                start_ip = ipaddress.ip_address(start_str)
                if "." not in end_str:
                    base_parts = start_str.split(".")
                    base_parts[-1] = end_str
                    end_str = ".".join(base_parts)
                end_ip = ipaddress.ip_address(end_str)
                
                if start_ip > end_ip:
                    start_ip, end_ip = end_ip, start_ip
                
                start_int = int(start_ip)
                end_int = int(end_ip)
                
                # Sınırlandırma
                if end_int - start_int > 256:
                    end_int = start_int + 256
                
                return [str(ipaddress.ip_address(i)) for i in range(start_int, end_int + 1)]
            except ValueError:
                pass

    # Virgülle ayrılmış liste veya tek IP
    ips = []
    for part in ip_range.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ipaddress.ip_address(part)
            ips.append(part)
        except ValueError:
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,251}", part):
                ips.append(part)
    return ips[:256]

async def check_port_async(ip: str, port: int, timeout: float = 1.5) -> bool:
    """Belirtilen IP ve portun açık olup olmadığını asenkron kontrol eder."""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False

async def check_rtsp_path_async(
    ip: str, port: int, path: str, username: str = "", password: str = "", timeout: float = 1.5,
    frame_fallback: bool = True,
) -> bool:
    """
    Bir RTSP path'inin geçerli olup olmadığını asenkron TCP soketiyle doğrular.
    RTSP DESCRIBE isteği gönderir ve 200 OK veya 401 Unauthorized (Digest/Basic tetikleyerek) dönerse doğrular.

    frame_fallback=False: auth başarısız olunca OpenCV fallback denenmez (NVR tarama için önerilir).
    """
    path = path if path.startswith("/") else f"/{path}"
    url = f"rtsp://{ip}:{port}{path}"
    # İlk istek kimlik bilgisiz gönderilir (standart el sıkışma)
    req = (
        f"DESCRIBE {url} RTSP/1.0\r\n"
        f"CSeq: 1\r\n"
        f"Accept: application/sdp\r\n"
        f"User-Agent: KameraYonetimiScanner/1.0\r\n\r\n"
    )

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout
        )
        writer.write(req.encode())
        await writer.drain()
        
        response = await asyncio.wait_for(reader.read(1024), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        
        res_text = response.decode(errors='ignore')
        status_line = res_text.splitlines()[0] if res_text else ""
        
        # 200 OK doğrudan geçerli (anonim erişime izin veriliyor)
        if "200" in status_line:
            return True
            
        # 401 Unauthorized ise şifreli doğrulamayı dene
        if "401" in status_line and username and password:
            # Tırnaklı veya tırnaksız realm/nonce eşleştirmeleri için esnek regex
            realm_match = re.search(r'realm="?([^",\s]+)"?', res_text, re.IGNORECASE)
            nonce_match = re.search(r'nonce="?([^",\s]+)"?', res_text, re.IGNORECASE)
            
            # 1) Digest Yetkilendirmesi
            if "digest" in res_text.lower() and realm_match and nonce_match:
                realm = realm_match.group(1)
                nonce = nonce_match.group(1)

                # Modern Hikvision/Dahua qop=auth kullanır; bu durumda nc+cnonce+qop gerekir
                qop_match = re.search(r'qop="?([^",\s]+)"?', res_text, re.IGNORECASE)
                qop = qop_match.group(1) if qop_match else None
                use_qop = qop and "auth" in qop.lower()

                # Cihaza göre tam URL veya sadece path denenir
                for auth_uri in [url, path]:
                    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
                    ha2 = hashlib.md5(f"DESCRIBE:{auth_uri}".encode()).hexdigest()

                    if use_qop:
                        nc = "00000001"
                        cnonce = hashlib.md5(os.urandom(8)).hexdigest()[:8]
                        auth_response = hashlib.md5(
                            f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()
                        ).hexdigest()
                        digest_header = (
                            f'Authorization: Digest username="{username}", realm="{realm}", '
                            f'nonce="{nonce}", uri="{auth_uri}", qop={qop}, '
                            f'nc={nc}, cnonce="{cnonce}", response="{auth_response}"'
                        )
                    else:
                        auth_response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
                        digest_header = (
                            f'Authorization: Digest username="{username}", realm="{realm}", '
                            f'nonce="{nonce}", uri="{auth_uri}", response="{auth_response}"'
                        )
                    
                    req_digest = (
                        f"DESCRIBE {url} RTSP/1.0\r\n"
                        f"CSeq: 2\r\n"
                        f"Accept: application/sdp\r\n"
                        f"User-Agent: KameraYonetimiScanner/1.0\r\n"
                        f"{digest_header}\r\n\r\n"
                    )
                    
                    try:
                        r2, w2 = await asyncio.wait_for(
                            asyncio.open_connection(ip, port),
                            timeout=timeout
                        )
                        w2.write(req_digest.encode())
                        await w2.drain()
                        resp2 = await asyncio.wait_for(r2.read(1024), timeout=timeout)
                        w2.close()
                        try:
                            await w2.wait_closed()
                        except Exception:
                            pass
                        
                        res_text2 = resp2.decode(errors='ignore')
                        status_line2 = res_text2.splitlines()[0] if res_text2 else ""
                        if "200" in status_line2:
                            return True
                    except Exception:
                        pass
                if frame_fallback:
                    return await validate_rtsp_endpoint_async(ip, port, path, username, password)
                return False

            # 2) Basic Yetkilendirmesi (i610 / IPNC vb. cihazlar için)
            elif "basic" in res_text.lower():
                auth_bytes = f"{username}:{password}".encode()
                auth_str = base64.b64encode(auth_bytes).decode()
                req_basic = (
                    f"DESCRIBE {url} RTSP/1.0\r\n"
                    f"CSeq: 2\r\n"
                    f"Accept: application/sdp\r\n"
                    f"User-Agent: KameraYonetimiScanner/1.0\r\n"
                    f"Authorization: Basic {auth_str}\r\n\r\n"
                )
                
                try:
                    r2, w2 = await asyncio.wait_for(
                        asyncio.open_connection(ip, port),
                        timeout=timeout
                    )
                    w2.write(req_basic.encode())
                    await w2.drain()
                    resp2 = await asyncio.wait_for(r2.read(1024), timeout=timeout)
                    w2.close()
                    try:
                        await w2.wait_closed()
                    except Exception:
                        pass
                    
                    res_text2 = resp2.decode(errors='ignore')
                    status_line2 = res_text2.splitlines()[0] if res_text2 else ""
                    if "200" in status_line2:
                        return True
                except Exception:
                    pass
        if status_line and "401" not in status_line:
            return False
        if not frame_fallback:
            return False
        return await validate_rtsp_endpoint_async(ip, port, path, username, password)
    except Exception:
        if not frame_fallback:
            return False
        return await validate_rtsp_endpoint_async(ip, port, path, username, password)

async def find_working_rtsp_path_async(
    ip: str, port: int = 554, username: str = "", password: str = "", auto_ports: bool = False
) -> Dict[str, Any] | None:
    """Bir cihaz için bilinen RTSP yollarından çalışan ilk yolu döner."""
    for candidate_port in build_candidate_ports(port, auto_ports):
        for p_info in load_rtsp_paths():
            path = p_info["path"]
            if await check_rtsp_path_async(ip, candidate_port, path, username, password):
                return {
                    "ip": ip,
                    "port": candidate_port,
                    "path": path,
                    "brand": p_info.get("brand", "Generic"),
                    "desc": p_info.get("desc", ""),
                    "url": build_rtsp_url(ip, candidate_port, path, username, password),
                }
    return None

async def scan_single_ip(
    ip: str, ports: List[int], paths: List[Dict[str, str]], username: str = "", password: str = ""
) -> List[Dict[str, Any]]:
    """Tekil bir IP üzerinde RTSP portunu tarar ve eşleşen yolları bulur."""
    found_streams = []
    for port in ports:
        if not await check_port_async(ip, port, timeout=0.8):
            continue
        for p_info in paths:
            path = p_info["path"]
            success = await check_rtsp_path_async(ip, port, path, username, password)
            if success:
                found_streams.append({
                    "ip": ip,
                    "port": port,
                    "path": path,
                    "brand": p_info.get("brand", "Generic"),
                    "desc": p_info.get("desc", ""),
                    "url": build_rtsp_url(ip, port, path, username, password)
                })
                return found_streams

    return found_streams

async def scan_cameras_async(
    ip_range: str, rtsp_port: int = 554, username: str = "", password: str = "", auto_ports: bool = False
) -> List[Dict[str, Any]]:
    """Tüm IP aralığını asenkron ve paralel olarak tarar."""
    ips = parse_ip_range(ip_range)
    if not ips:
        return []

    paths = load_rtsp_paths()
    ports = build_candidate_ports(rtsp_port, auto_ports)
    tasks = [scan_single_ip(ip, ports, paths, username, password) for ip in ips]
    
    # 30'lu gruplar halinde tarama yaparak soket limiti aşımını engelle
    chunk_size = 30
    results = []
    for i in range(0, len(tasks), chunk_size):
        chunk = tasks[i:i + chunk_size]
        chunk_results = await asyncio.gather(*chunk)
        for r in chunk_results:
            if r:
                results.extend(r)
                
    return results


async def scan_nvr_channels_async(
    host: str, rtsp_port: int = 554, username: str = "", password: str = "", max_channels: int = 16
) -> List[Dict[str, Any]]:
    """
    NVR üzerindeki aktif RTSP kanallarını şablonlara göre tarar.
    frame_fallback=False: OpenCV fallback denenmez, NVR overwhelmed olmaz.
    """
    # Hem standart RTSP portu hem VideoEdge'e özgü 7778 portunu dene
    active_ports = []
    for p in [rtsp_port, 7778] if rtsp_port != 7778 else [rtsp_port]:
        if await check_port_async(host, p):
            active_ports.append(p)
    if not active_ports:
        return []

    templates = [
        {"template": "/media/{channel}/video/1", "brand": "VideoEdge NVR", "desc": "Channel {channel} main"},
        {"template": "/Streaming/Channels/{channel}01", "brand": "Hikvision NVR", "desc": "Channel {channel} main"},
        {"template": "/cam/realmonitor?channel={channel}&subtype=0", "brand": "Dahua NVR", "desc": "Channel {channel} main"},
        {"template": "/live/ch{channel}", "brand": "Generic NVR", "desc": "Channel {channel}"},
        {"template": "/ch{channel}", "brand": "Generic NVR", "desc": "Channel {channel}"},
    ]

    tasks = []
    task_info = []
    for scan_port in active_ports:
        for ch in range(1, max_channels + 1):
            for t in templates:
                path = t["template"].format(channel=ch)
                tasks.append(check_rtsp_path_async(host, scan_port, path, username, password, frame_fallback=False))
                task_info.append({
                    "channel": ch,
                    "path": path,
                    "brand": t["brand"],
                    "desc": t["desc"].format(channel=ch),
                    "port": scan_port,
                })

    chunk_size = 10  # Küçük chunk: NVR overwhelmed olmasın
    found_channels = []
    for i in range(0, len(tasks), chunk_size):
        chunk_tasks = tasks[i:i + chunk_size]
        chunk_info = task_info[i:i + chunk_size]
        chunk_results = await asyncio.gather(*chunk_tasks)
        for success, info in zip(chunk_results, chunk_info):
            if success:
                found_channels.append({
                    "profile_token": f"ch_{info['channel']}_{info['brand'].replace(' ', '_')}",
                    "profile_name": f"Kanal {info['channel']} ({info['brand']})",
                    "manufacturer": info["brand"],
                    "model": "RTSP Stream",
                    "rtsp_url": build_rtsp_url(host, info["port"], info["path"], username, password)
                })

    unique_channels = {}
    for ch in found_channels:
        parts = ch["profile_name"].split(" ")
        if len(parts) >= 2:
            ch_num = parts[1]
            if ch_num not in unique_channels:
                unique_channels[ch_num] = ch

    sorted_keys = sorted(unique_channels.keys(), key=lambda x: int(x) if x.isdigit() else 999)
    return [unique_channels[k] for k in sorted_keys]


async def scan_single_ip_for_nvr(
    ip: str, port: int, check_paths: list, username: str, password: str
) -> Dict[str, Any] | None:
    """Tekil bir IP üzerinde NVR şablonlarını test eder."""
    is_open = await check_port_async(ip, port)
    if not is_open:
        return None

    for p_info in check_paths:
        success = await check_rtsp_path_async(ip, port, p_info["path"], username, password)
        if success:
            # Yaygın ONVIF portlarını sırayla kontrol ederek NVR yönetim portunu tespit et
            onvif_port = 80
            for candidate_onvif in [80, 8080, 8000]:
                if await check_port_async(ip, candidate_onvif, timeout=0.8):
                    onvif_port = candidate_onvif
                    break
            return {
                "host": ip,
                "port": onvif_port,
                "brand": p_info["brand"],
                "model": "Network Video Recorder"
            }
    return None


async def scan_nvrs_async(
    ip_range: str, rtsp_port: int = 554, username: str = "", password: str = ""
) -> List[Dict[str, Any]]:
    """Tüm IP aralığını NVR cihazları için asenkron tarar."""
    ips = parse_ip_range(ip_range)
    if not ips:
        return []

    # Her marka için 1. kanalı denemek NVR tespiti için yeterlidir
    nvr_check_paths = [
        { "path": "/media/1/video/1", "brand": "VideoEdge NVR" },
        { "path": "/Streaming/Channels/101", "brand": "Hikvision NVR" },
        { "path": "/cam/realmonitor?channel=1&subtype=0", "brand": "Dahua NVR" }
    ]

    tasks = [scan_single_ip_for_nvr(ip, rtsp_port, nvr_check_paths, username, password) for ip in ips]

    chunk_size = 30
    results = []
    for i in range(0, len(tasks), chunk_size):
        chunk = tasks[i:i + chunk_size]
        chunk_results = await asyncio.gather(*chunk)
        for r in chunk_results:
            if r:
                results.append(r)
                
    return results
