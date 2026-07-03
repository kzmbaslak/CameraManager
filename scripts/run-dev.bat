@echo off
REM Kamera Yönetimi Sistemi - Geliştirme Modu
REM Development Mode (Auto-reload etkin)

setlocal enabledelayedexpansion

cd /d "%~dp0..\backend"

if not exist venv (
    echo [ERROR] venv klasoru bulunamadi. Lutfen backend klasorunde venv olusturun.
    pause
    exit /b 1
)

echo [INFO] Virtual environment aktivasyon...
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo [ERROR] venv aktivasyonu basarisiz oldu.
    pause
    exit /b 1
)

echo [INFO] API sunucusu baslatiliyor (Gelistirme Modu)...
echo [INFO] http://127.0.0.1:8090 adresinde erisilebilir
echo [INFO] http://127.0.0.1:8090/docs - Swagger UI
echo [INFO] Durdurmak icin: CTRL+C
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8090 --reload

pause
