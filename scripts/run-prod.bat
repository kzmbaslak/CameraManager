@echo off
REM Kamera Yönetimi Sistemi - Üretim Modu
REM Production Mode (Yüksek performans, reload devre disi)

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

echo [INFO] API sunucusu baslatiliyor (Uretim Modu)...
echo [INFO] http://127.0.0.1:8000 adresinde erisilebilir
echo [INFO] Durdurmak icin: CTRL+C
echo.

REM --workers verilmez: CameraStreamManager process-ici (in-memory) tek
REM instance bekler; coklu worker process ile kamera basina birden fazla
REM RTSP baglantisi acilir ve kare/alarm durumu surecler arasinda tutarsiz olur.
python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
