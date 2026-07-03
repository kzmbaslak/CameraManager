"""
FastAPI bağımlılık (dependency injection) yapılandırması.

Bu modül, uygulama genelinde kullanılan servis instance'larını (singleton)
ve her HTTP isteği için taze repository/use-case örnekleri döndüren
factory fonksiyonlarını içerir.

Singleton servisler uygulama ömrü boyunca tek bir kez oluşturulur:
  - password_service  → AES-256-GCM şifreleme/çözme
  - frame_source      → RTSP akış okuyucu (OpenCV) — tekil kare okuma istekleri için
  - ai_service        → ONNX YOLOv8 AI çıkarım servisi
  - stream_manager    → Kamera başına TEK RTSP bağlantısı açan, AI tespiti yapan ve
                         tüm WebSocket izleyicilerine kare yayınlayan (broadcast) yönetici
  - health_checker    → Tüm aktif kameralara periyodik TCP ping (online/offline takibi)
  - nvr_probe_service → ONVIF cihaz sorgulama servisi

Repository ve use-case'ler her istekte FastAPI Depends() mekanizmasıyla
taze veritabanı oturumu (Session) ile oluşturulur.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.infrastructure.database.database import get_db
from src.infrastructure.database.repositories.camera_repository import SqlAlchemyCameraRepository
from src.infrastructure.database.repositories.alarm_repository import SqlAlchemyAlarmRepository
from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from src.infrastructure.database.repositories.nvr_repository import SqlAlchemyNVRRepository
from src.application.use_cases.camera_use_cases import CameraUseCases
from src.application.use_cases.nvr_use_cases import NVRUseCases
from src.application.use_cases.frame_processing_use_case import ProcessFrameUseCase
from src.infrastructure.camera.opencv_stream_reader import OpenCVStreamReader
from src.infrastructure.ai.onnx_inference_service import ONNXInferenceService
from src.infrastructure.onvif.onvif_probe_service import ONVIFProbeService
from src.application.services.camera_stream_manager import CameraStreamManager
from src.application.services.camera_health_checker import CameraHealthChecker
from src.infrastructure.security.password_service import PasswordEncryptionService

# ---------------------------------------------------------------------------
# Singleton altyapı servisleri (uygulama boyunca tek instance)
# ---------------------------------------------------------------------------
password_service = PasswordEncryptionService()
frame_source = OpenCVStreamReader(password_service=password_service)
ai_service = ONNXInferenceService()
stream_manager = CameraStreamManager(ai_service=ai_service, password_service=password_service)
nvr_probe_service = ONVIFProbeService()
health_checker = CameraHealthChecker(check_interval=10.0, timeout=3.0, cooldown_seconds=60)


# ---------------------------------------------------------------------------
# Repository factory'leri — her HTTP isteğinde taze DB session ile çalışır
# ---------------------------------------------------------------------------

def get_camera_repository(db: Session = Depends(get_db)) -> SqlAlchemyCameraRepository:
    """Kamera CRUD işlemleri için SQLAlchemy repository döner."""
    return SqlAlchemyCameraRepository(db)

def get_alarm_repository(db: Session = Depends(get_db)) -> SqlAlchemyAlarmRepository:
    """Alarm CRUD işlemleri için SQLAlchemy repository döner."""
    return SqlAlchemyAlarmRepository(db)

def get_user_repository(db: Session = Depends(get_db)) -> SqlAlchemyUserRepository:
    """Kullanıcı CRUD işlemleri için SQLAlchemy repository döner."""
    return SqlAlchemyUserRepository(db)

def get_nvr_repository(db: Session = Depends(get_db)) -> SqlAlchemyNVRRepository:
    """NVR CRUD işlemleri için SQLAlchemy repository döner."""
    return SqlAlchemyNVRRepository(db)


# ---------------------------------------------------------------------------
# Use case factory'leri
# ---------------------------------------------------------------------------

def get_password_service() -> PasswordEncryptionService:
    """AES-256 şifre servisi singleton'ını döner."""
    return password_service

def get_camera_use_cases(
    repo: SqlAlchemyCameraRepository = Depends(get_camera_repository),
) -> CameraUseCases:
    """Kamera iş mantığı use case'ini, password_service ile birlikte döner."""
    return CameraUseCases(repo, password_service=password_service)

def get_nvr_use_cases(
    repo: SqlAlchemyNVRRepository = Depends(get_nvr_repository),
) -> NVRUseCases:
    """NVR iş mantığı use case'ini, password_service ile birlikte döner."""
    return NVRUseCases(repo, password_service=password_service)

def get_frame_processing_use_case(
    camera_repo: SqlAlchemyCameraRepository = Depends(get_camera_repository),
    alarm_repo: SqlAlchemyAlarmRepository = Depends(get_alarm_repository),
) -> ProcessFrameUseCase:
    """Görüntü işleme ve AI tespit use case'ini döner."""
    return ProcessFrameUseCase(
        camera_repository=camera_repo,
        alarm_repository=alarm_repo,
        frame_source=frame_source,
        ai_service=ai_service,
    )

def get_stream_manager() -> CameraStreamManager:
    """Kamera canlı akış/AI tespit yöneticisini döner."""
    return stream_manager

def get_nvr_probe_service() -> ONVIFProbeService:
    """ONVIF cihaz sorgulama servisini döner."""
    return nvr_probe_service


# ---------------------------------------------------------------------------
# JWT kimlik doğrulama dependency'si
# ---------------------------------------------------------------------------

from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from src.infrastructure.security.jwt_service import decode_access_token

_bearer = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> dict:
    """
    Authorization: Bearer <token> başlığından JWT'yi okur ve doğrular.
    Geçersiz veya eksik token durumunda 401 döner.
    Dönen dict: {"sub": username, "role": role}
    """
    from fastapi import HTTPException, status
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kimlik doğrulama gerekli.")
    try:
        payload = decode_access_token(credentials.credentials)
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz veya süresi dolmuş token.")


def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Kullanıcının 'admin' rolüne sahip olup olmadığını doğrular."""
    from fastapi import HTTPException, status
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Admin yetkisi gereklidir."
        )
    return current_user


def get_operator_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Kullanıcının 'admin' veya 'operator' rolüne sahip olup olmadığını doğrular."""
    from fastapi import HTTPException, status
    if current_user.get("role") not in ["admin", "operator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için Admin veya Operatör yetkisi gereklidir."
        )
    return current_user

