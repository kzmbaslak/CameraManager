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
from src.presentation.api.dependencies import password_service

def debug():
    db = SessionLocal()
    cam_repo = SqlAlchemyCameraRepository(db)
    nvr_repo = SqlAlchemyNVRRepository(db)

    print("=== NVRS ===")
    nvrs = nvr_repo.list_all()
    for n in nvrs:
        pw = ""
        if n.encrypted_password:
            try:
                pw = password_service.decrypt(n.encrypted_password)
            except Exception as e:
                pw = f"[DECRYPT ERROR: {e}]"
        print(f"ID: {n.id} | Name: {n.name} | Host: {n.host} | Port: {n.onvif_port} | User: {n.username} | Pass: {pw}")

    print("\n=== CAMERAS ===")
    cameras = cam_repo.list_all()
    for c in cameras:
        pw = ""
        if c.encrypted_password:
            try:
                pw = password_service.decrypt(c.encrypted_password)
            except Exception as e:
                pw = f"[DECRYPT ERROR: {e}]"
        
        # Build RTSP URL
        auth = ""
        if c.username and c.encrypted_password:
            auth = f"{c.username}:{pw}@"
        rtsp_url = f"rtsp://{auth}{c.host}:{c.rtsp_port}{c.rtsp_path}"
        
        print(f"ID: {c.id} | Name: {c.name} | Host: {c.host} | Port: {c.rtsp_port} | Path: {c.rtsp_path} | User: {c.username} | Pass: {pw} | NVR_ID: {c.nvr_id}")
        print(f"  --> Built RTSP URL: {rtsp_url}")
    
    db.close()

if __name__ == "__main__":
    debug()
