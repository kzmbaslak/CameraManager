@echo off
REM Musteri Paketi Olusturucu — Kamera Yonetimi Sistemi
REM
REM Bu dosyayi SADECE internet baglantisi olan GELISTIRME bilgisayaninda
REM calistirin. Frontend'i derler, Python'un "embeddable" dagitimini indirir,
REM backend venv bagimliliklarini bu dagitimin icine kopyalar ve
REM "customer_package\KameraYonetimi" klasorunde / zip'inde, musteri
REM bilgisayarinda INTERNET GEREKTIRMEDEN calisacak tam bir paket uretir.

setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_customer_package.ps1"
if errorlevel 1 (
    echo.
    echo [HATA] Paketleme basarisiz oldu. Yukaridaki mesajlari kontrol edin.
    if "%MUSTERI_PAKETLE_NO_PAUSE%"=="1" exit /b 1
    pause
    exit /b 1
)

echo.
echo Paketleme tamamlandi.
if "%MUSTERI_PAKETLE_NO_PAUSE%"=="1" exit /b 0
pause
