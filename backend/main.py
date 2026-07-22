# Konsol kod sayfasi (ozellikle Turkce Windows'ta cp1254) emoji/Turkce
# karakter icin yetersiz kalip UnicodeEncodeError firlatabiliyor — once
# stdout/stderr'i UTF-8'e zorla. Diger tum importlardan ONCE olmali.
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import os
# OPENCV_FFMPEG_CAPTURE_OPTIONS: tüm cv2/FFmpeg import'larından ÖNCE set edilmeli.
# stimeout = RTSP socket timeout (µs). rtsp_transport=tcp → nat/firewall uyumlu,
# thread-safe (tek process-wide değer, thread başına değiştirilmiyor).
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "timeout;5000000|stimeout;5000000|rw_timeout;5000000|rtsp_transport;tcp"
)

# .env dosyasını oku — diğer tüm importlardan ÖNCE olmalı
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.presentation.api import router as api_router
from src.infrastructure.database.database import engine, ensure_camera_ai_settings_columns
from src.infrastructure.database import models
from src.infrastructure.security.runtime_config import validate_security_environment

# Veritabanı tablolarını oluştur
validate_security_environment()
models.Base.metadata.create_all(bind=engine)
ensure_camera_ai_settings_columns()


def _seed_admin_user() -> None:
    """Env ile açıkça istenirse ilk admin kullanıcısını oluştur."""
    import bcrypt
    from src.infrastructure.database.database import SessionLocal
    from src.infrastructure.database.models import UserModel
    from src.domain.entities.user import UserRole

    initial_username = os.environ.get("INITIAL_ADMIN_USERNAME", "").strip()
    initial_password = os.environ.get("INITIAL_ADMIN_PASSWORD", "")

    db = SessionLocal()
    try:
        if db.query(UserModel).count() == 0:
            if not initial_username or not initial_password:
                print(
                    "[Setup] Kullanıcı bulunamadı. İlk admin için "
                    "INITIAL_ADMIN_USERNAME ve INITIAL_ADMIN_PASSWORD env değerlerini "
                    "tanımlayın veya backend/scripts/create_user.py komutunu kullanın."
                )
                return
            password_hash = bcrypt.hashpw(initial_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            admin = UserModel(
                username=initial_username,
                password_hash=password_hash,
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"[Setup] İlk admin kullanıcısı oluşturuldu: {initial_username}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başlangıç ve kapanış yönetimi."""
    _seed_admin_user()
    from src.presentation.api.dependencies import stream_manager, health_checker
    await stream_manager.start_all_active()
    health_checker.start()
    yield
    health_checker.stop()
    await stream_manager.stop_all()


def create_app() -> FastAPI:
    cors_origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ]
    app = FastAPI(
        title="Güvenlik Kamera İzleme ve İnsan Tespiti",
        description="Local NVR ve AI Destekli İnsan Tespiti Sistemi",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(api_router, prefix="/api")

    # Production: frontend/dist/ klasörünü statik olarak sun
    # API router'dan SONRA tanımlanmalı — yoksa /api isteklerini yakalar
    dist_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    if os.path.isdir(dist_path):
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        assets_path = os.path.join(dist_path, "assets")
        if os.path.isdir(assets_path):
            app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

        index_file = os.path.join(dist_path, "index.html")

        @app.get("/{full_path:path}")
        def serve_spa(full_path: str):
            """
            SPA fallback: gerçek bir statik dosya varsa onu sun, yoksa index.html
            döndür — böylece /login, /cameras gibi client-side route'lar
            doğrudan tarayıcı adres çubuğundan açıldığında 404 vermez.
            """
            candidate = os.path.join(dist_path, full_path)
            if full_path and os.path.isfile(candidate):
                return FileResponse(candidate)
            return FileResponse(index_file)
    else:
        @app.get("/")
        def root():
            return {"message": "Kamera İzleme Sistemi API Çalışıyor."}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8090, reload=True)
