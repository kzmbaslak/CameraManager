@echo off
REM Musteri Paketi Olusturucu — Kamera Yonetimi Sistemi
REM
REM Bu dosyayi SADECE internet baglantisi olan GELISTIRME bilgisayaninda
REM calistirin. Frontend'i derler, Python'un "embeddable" dagitimini indirir,
REM tum bagimliliklari (requirements.txt) bu dagitimin icine kurar ve
REM "customer_package\KameraYonetimi" klasorunde / zip'inde, musteri
REM bilgisayarinda INTERNET GEREKTIRMEDEN calisacak tam bir paket uretir.

setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_customer_package.ps1"
if errorlevel 1 (
    echo.
    echo [HATA] Paketleme basarisiz oldu. Yukaridaki mesajlari kontrol edin.
    pause
    exit /b 1
)

echo.
echo Paketleme tamamlandi.
pause
