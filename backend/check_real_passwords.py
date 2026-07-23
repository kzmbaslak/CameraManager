"""Kamera/NVR kimlik bilgisi envanterini hassas veri sizdirmadan raporlar."""

import sys
import os

# backend'i sys.path'e ekleyelim
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# .env dosyasını yükle
from dotenv import load_dotenv
load_dotenv()

from src.infrastructure.database.database import SessionLocal
from src.infrastructure.database.repositories.camera_repository import SqlAlchemyCameraRepository
from src.infrastructure.database.repositories.nvr_repository import SqlAlchemyNVRRepository


def _mask_username(username: str | None) -> str:
    """Kullanici adini tam degeri sizdirmeden kisa bir ipucuna cevirir."""
    if not username:
        return "-"
    if len(username) <= 2:
        return "***"
    return f"{username[:2]}***"


def _masked_rtsp_url(camera) -> str:
    """Kamera RTSP adresini parola veya tam kullanici adi yazmadan uretir."""
    auth = "user:***@" if camera.username and camera.encrypted_password else ""
    return f"rtsp://{auth}{camera.host}:{camera.rtsp_port}{camera.rtsp_path}"


def debug():
    """Kamera/NVR kayitlarinda parola varligini ve maskeli baglanti bilgisini listeler."""
    db = SessionLocal()
    try:
        cam_repo = SqlAlchemyCameraRepository(db)
        nvr_repo = SqlAlchemyNVRRepository(db)

        print("=== NVRS ===")
        nvrs = nvr_repo.list_all()
        for n in nvrs:
            password_state = "configured" if n.encrypted_password else "missing"
            print(
                f"ID: {n.id} | Name: {n.name} | Host: {n.host} | Port: {n.onvif_port} | "
                f"User: {_mask_username(n.username)} | Password: {password_state} | "
                f"RotatedAt: {n.password_updated_at or '-'}"
            )

        print("\n=== CAMERAS ===")
        cameras = cam_repo.list_all()
        for c in cameras:
            password_state = "configured" if c.encrypted_password else "missing"
            print(
                f"ID: {c.id} | Name: {c.name} | Host: {c.host} | Port: {c.rtsp_port} | "
                f"Path: {c.rtsp_path} | User: {_mask_username(c.username)} | "
                f"Password: {password_state} | RotatedAt: {c.password_updated_at or '-'} | NVR_ID: {c.nvr_id}"
            )
            print(f"  --> Masked RTSP URL: {_masked_rtsp_url(c)}")
    finally:
        db.close()

if __name__ == "__main__":
    debug()
