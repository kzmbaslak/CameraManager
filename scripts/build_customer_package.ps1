# Musteri Paketi Olusturucu - Kamera Yonetimi Sistemi
#
# Bu script, internet erisimi OLMAYAN musteri bilgisayarlarinda calistirilabilecek
# tamamen kendi icinde (self-contained) bir paket uretir:
#   - Frontend derlenir (npm run build) -> backend FastAPI tarafindan statik sunulur
#   - Python'un "embeddable" dagitimi indirilir ve backend venv bagimliliklari
#     bu dagitimin icine kopyalanir -> musteri bilgisayarinda
#     Python kurulu olmasi GEREKMEZ, "py install" gibi internetten indirme
#     yapan hicbir komut musteri tarafinda calismaz.
#   - Sonuc klasor "Calistir.bat" ile dogrudan calistirilabilir.
#
# Bu scripti SADECE internet baglantisi olan GELISTIRME bilgisayaninda calistirin.
# Uretilen paket musteri bilgisayarina kopyalandiginda hicbir indirme islemi
# yapmadan calismalidir.

$ErrorActionPreference = "Stop"

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$BackendSrc = Join-Path $RepoRoot "backend"
$FrontendSrc = Join-Path $RepoRoot "frontend"

$PythonVersion = "3.14.2"               # backend/venv ile ayni surum (ABI uyumu icin)
$PythonEmbedUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$OutDir = Join-Path $RepoRoot "customer_package"
$PkgDir = Join-Path $OutDir "KameraYonetimi"
$CacheDir = Join-Path $RepoRoot "scripts\cache"
if (-not (Test-Path $CacheDir)) { New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null }

Write-Host "==> Eski paket temizleniyor..." -ForegroundColor Cyan
if (Test-Path $OutDir) {
    Get-ChildItem -Path $OutDir | ForEach-Object {
        try {
            Remove-Item $_.FullName -Recurse -Force -ErrorAction Stop
        } catch {
            Write-Host "[UYARI] '$($_.Name)' silinemedi (Dosya kilitli olabilir): $_" -ForegroundColor Yellow
        }
    }
}
if (-not (Test-Path $PkgDir)) {
    New-Item -ItemType Directory -Path $PkgDir -Force | Out-Null
}

# ---------------------------------------------------------------------------
# 1) Frontend derleme
# ---------------------------------------------------------------------------
Write-Host "==> Frontend derleniyor (npm run build)..." -ForegroundColor Cyan

# Bu makinede Node.js, nvm4w ile yonetiliyor ve PATH'e her zaman eklenmemis
# olabilir (ozellikle bu script bagimsiz bir powershell.exe sureci olarak
# calistirildiginda). npm bulunamazsa bilinen nvm4w konumunu PATH'e ekle.
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    $nvm4wLink = "C:\nvm4w\nodejs"
    if (Test-Path $nvm4wLink) {
        $env:PATH = "$nvm4wLink;$env:PATH"
    }
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm bulunamadi. Node.js kurulu oldugundan ve PATH'te oldugundan emin olun."
}

Push-Location $FrontendSrc
try {
    if (-not (Test-Path "node_modules")) {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install basarisiz oldu." }
    }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build basarisiz oldu." }
} finally {
    Pop-Location
}

# ---------------------------------------------------------------------------
# 2) Backend kaynak kodunu PyArmor ile şifreleyerek kopyala
# ---------------------------------------------------------------------------
Write-Host "==> Backend kaynak kodu şifreleniyor (PyArmor)..." -ForegroundColor Cyan
$PkgBackend = Join-Path $PkgDir "backend"
New-Item -ItemType Directory -Path $PkgBackend -Force | Out-Null

$PlainSourceFallback = $false
$PyArmorExe = Join-Path $RepoRoot "backend\venv\Scripts\pyarmor.exe"
if (-not (Test-Path $PyArmorExe)) {
    Write-Host "[UYARI] pyarmor.exe bulunamadi; calisir musteri paketi icin kaynak kod plain olarak kopyalaniyor." -ForegroundColor Yellow
    $PlainSourceFallback = $true
}

if (-not $PlainSourceFallback) {
    Push-Location $BackendSrc
    try {
        # main.py ve src klasorundeki kodlari sifreleyerek cikti klasorune yaz.
        $PyArmorLogPath = Join-Path $CacheDir "pyarmor-package.log"
        $PreviousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & $PyArmorExe gen -O $PkgBackend -r main.py src > $PyArmorLogPath 2>&1
            $PyArmorExitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $PreviousErrorActionPreference
        }
        if ($PyArmorExitCode -ne 0) {
            Write-Host "[UYARI] PyArmor sifreleme basarisiz oldu; calisir musteri paketi icin kaynak kod plain olarak kopyalaniyor." -ForegroundColor Yellow
            Write-Host "        Ayrinti: scripts\cache\pyarmor-package.log" -ForegroundColor Yellow
            $PlainSourceFallback = $true
        }
    } finally {
        Pop-Location
    }
}

if ($PlainSourceFallback) {
    Copy-Item (Join-Path $BackendSrc "main.py") $PkgBackend -Force
    robocopy (Join-Path $BackendSrc "src") (Join-Path $PkgBackend "src") /E /NFL /NDL /NJH /NJS /NC /NS | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Backend kaynak kodu kopyalama hatasi (robocopy kod: $LASTEXITCODE)" }
}

# Diğer backend klasörlerini (models, scripts vb.) ve gereksinimleri kopyala
Write-Host "==> Diğer backend bileşenleri kopyalanıyor..." -ForegroundColor Cyan
$BackendFoldersToCopy = @("models", "scripts")
foreach ($folder in $BackendFoldersToCopy) {
    $srcFolder = Join-Path $BackendSrc $folder
    $dstFolder = Join-Path $PkgBackend $folder
    if (Test-Path $srcFolder) {
        New-Item -ItemType Directory -Path $dstFolder -Force | Out-Null
        robocopy $srcFolder $dstFolder /E /NFL /NDL /NJH /NJS /NC /NS | Out-Null
    }
}

Copy-Item (Join-Path $BackendSrc "requirements.txt") $PkgBackend -Force

# data klasorunu olustur ve yalnizca statik RTSP path verisini kopyala.
# Veritabani, audit log ve runtime kayitlari musteri paketine tasinmaz.
$srcData = Join-Path $BackendSrc "data"
$dstData = Join-Path $PkgBackend "data"
New-Item -ItemType Directory -Path $dstData -Force | Out-Null
if (-not (Test-Path $srcData)) {
    throw "backend/data/ klasoru bulunamadi. Statik RTSP path verileri olmadan paket olusturulamaz."
}

$srcRtspPaths = Join-Path $srcData "rtsp_paths.json"
$dstRtspPaths = Join-Path $dstData "rtsp_paths.json"
if (-not (Test-Path $srcRtspPaths)) {
    throw "Kaynak backend/data/rtsp_paths.json bulunamadi."
}
Copy-Item $srcRtspPaths $dstRtspPaths -Force
if (-not (Test-Path $dstRtspPaths)) {
    throw "Paket dogrulamasi basarisiz: backend/data/rtsp_paths.json hedefe kopyalanmadi."
}

$srcRtspHash = (Get-FileHash -Path $srcRtspPaths -Algorithm SHA256).Hash
$dstRtspHash = (Get-FileHash -Path $dstRtspPaths -Algorithm SHA256).Hash
if ($srcRtspHash -ne $dstRtspHash) {
    throw "Paket dogrulamasi basarisiz: rtsp_paths.json kaynak ve hedef dosyalari farkli."
}
Write-Host "==> rtsp_paths.json kopyalandi ve dogrulandi." -ForegroundColor Green
# snapshots: uygulama ilk calismada doldurur, bos olustur
New-Item -ItemType Directory -Path (Join-Path $PkgBackend "snapshots") -Force | Out-Null

# ---------------------------------------------------------------------------
# 3) .env dosyasi - musteriye OZEL yeni rastgele anahtarlarla olustur
# ---------------------------------------------------------------------------
Write-Host "==> .env dosyasi (musteriye ozel anahtarlarla) olusturuluyor..." -ForegroundColor Cyan
Add-Type -AssemblyName System.Security
function New-RandomBase64($bytes) {
    $buf = New-Object byte[] $bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buf)
    return [System.Convert]::ToBase64String($buf)
}
function New-RandomHex($bytes) {
    $buf = New-Object byte[] $bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buf)
    return -join ($buf | ForEach-Object { $_.ToString("x2") })
}
$InitialAdminPassword = New-RandomHex 12
$envContent = @"
CAMERA_ENCRYPTION_KEY=$(New-RandomBase64 32)
JWT_SECRET_KEY=$(New-RandomHex 32)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=$InitialAdminPassword
"@
Set-Content -Path (Join-Path $PkgBackend ".env") -Value $envContent -Encoding ascii

# ---------------------------------------------------------------------------
# 4) Frontend dist kopyala
# ---------------------------------------------------------------------------
Write-Host "==> Frontend dist kopyalaniyor..." -ForegroundColor Cyan
$PkgFrontendDist = Join-Path $PkgDir "frontend\dist"
New-Item -ItemType Directory -Path $PkgFrontendDist -Force | Out-Null
robocopy (Join-Path $FrontendSrc "dist") $PkgFrontendDist /E /NFL /NDL /NJH /NJS /NC /NS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Frontend dist kopyalama hatasi (robocopy kod: $LASTEXITCODE)" }

# ---------------------------------------------------------------------------
# 5) Embeddable Python indir + cikar (Yerel önbellek destekli)
# ---------------------------------------------------------------------------
$PyZipPath = Join-Path $CacheDir "python-embed-$PythonVersion.zip"
if (-not (Test-Path $PyZipPath)) {
    Write-Host "==> Python $PythonVersion (embeddable) indiriliyor..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $PythonEmbedUrl -OutFile $PyZipPath -UseBasicParsing
} else {
    Write-Host "==> Python $PythonVersion (embeddable) yerel önbellekten kullanılıyor." -ForegroundColor Green
}

$VcRedistUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
$VcRedistPath = Join-Path $CacheDir "vc_redist.x64.exe"
if (-not (Test-Path $VcRedistPath)) {
    Write-Host "==> VC++ Redistributable 2015-2022 indiriliyor..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $VcRedistUrl -OutFile $VcRedistPath -UseBasicParsing
} else {
    Write-Host "==> VC++ Redistributable yerel önbellekten kullanılıyor." -ForegroundColor Green
}

$PyEmbedDir = Join-Path $PkgBackend "python"
New-Item -ItemType Directory -Path $PyEmbedDir -Force | Out-Null
Expand-Archive -Path $PyZipPath -DestinationPath $PyEmbedDir -Force

# site-packages'i etkinlestir: ._pth dosyasinda "import site" satirini ac.
# Ayrica ".." satirini ekle: embeddable python'da "." satiri her zaman
# python.exe'nin bulundugu klasore (burada backend\python) gore cozulur,
# CALISMA DIZININE (cwd) gore degil. Bu yuzden cwd=backend\ olarak
# baslatilsa bile "import main" basarisiz olur. ".." eklenince backend\
# klasoru de sys.path'e girer ve main.py her zaman bulunur.
$pthFile = Get-ChildItem -Path $PyEmbedDir -Filter "python*._pth" | Select-Object -First 1
if (-not $pthFile) { throw "._pth dosyasi bulunamadi. Embeddable python yapisi degisti mi?" }
(Get-Content $pthFile.FullName) -replace '^#import site$', 'import site' | Set-Content $pthFile.FullName -Encoding ascii
Add-Content -Path $pthFile.FullName -Value ".." -Encoding ascii

$PyExe = Join-Path $PyEmbedDir "python.exe"

# ---------------------------------------------------------------------------
# 6) Python bagimliliklarini paket icine al (musteri internet kullanmayacak)
# ---------------------------------------------------------------------------
$VenvSitePackages = Join-Path $BackendSrc "venv\Lib\site-packages"
if (-not (Test-Path $VenvSitePackages)) {
    throw "backend\venv\Lib\site-packages bulunamadi. Musteri paketi internet gerektirmemesi icin once backend venv bagimliliklarini kurun."
}

$PkgSitePackages = Join-Path $PyEmbedDir "Lib\site-packages"
New-Item -ItemType Directory -Path $PkgSitePackages -Force | Out-Null

Write-Host "==> Python bagimliliklari yerel venv'den paketleniyor..." -ForegroundColor Cyan
robocopy $VenvSitePackages $PkgSitePackages /E /XD "__pycache__" /XF "*.pyc" /NFL /NDL /NJH /NJS /NC /NS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Python bagimlilik kopyalama hatasi (robocopy kod: $LASTEXITCODE)" }

Write-Host "==> Python bagimliliklari dogrulaniyor (pip check)..." -ForegroundColor Cyan
& $PyExe -s -m pip check
if ($LASTEXITCODE -ne 0) { throw "Paket Python bagimlilik dogrulamasi basarisiz oldu." }

# ---------------------------------------------------------------------------
# 7) Calistir.bat - musteri bilgisayarinda tek tikla baslatma, INTERNET GEREKTIRMEZ
# ---------------------------------------------------------------------------
Write-Host "==> Calistir.bat olusturuluyor..." -ForegroundColor Cyan
$calistirBat = @"
@echo off
chcp 65001 >nul
title Kamera Yonetimi Sistemi
cd /d "%~dp0backend"

echo ============================================================
echo  Kamera Yonetimi Sistemi baslatiliyor...
echo  Adres: http://localhost:8090
echo  Ilk giris: admin / $InitialAdminPassword
echo  Guvenlik icin ilk giriste bu parolayi degistirin.
echo  Durdurmak icin bu pencereyi kapatin veya CTRL+C
echo ============================================================
echo.

start "" http://localhost:8090

REM --workers verilmez: kamera akis yoneticisi process-ici (in-memory)
REM tek instance bekler; coklu worker process ile kamera basina birden
REM fazla RTSP baglantisi acilir.
python\python.exe -s -m uvicorn main:app --host 0.0.0.0 --port 8090

pause
"@
Set-Content -Path (Join-Path $PkgDir "Calistir.bat") -Value $calistirBat -Encoding ascii

# 7.2) Durdur.bat - musteri bilgisayarinda arka plandaki python sunucusunu kapatma
Write-Host "==> Durdur.bat olusturuluyor..." -ForegroundColor Cyan
$durdurBat = @'
@echo off
chcp 65001 >nul
title Kamera Yonetimi Sistemi - Durdurma
echo ============================================================
echo  Kamera Yonetimi Sistemi durduruluyor...
echo ============================================================
echo.

set FOUND=0
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8090 .*LISTENING"') do (
    set FOUND=1
    taskkill /f /pid %%P >nul 2>&1
)

echo.
if "%FOUND%"=="1" (
    echo Sistem durduruldu.
) else (
    echo 8090 portunda calisan Kamera Yonetimi sureci bulunamadi.
)
echo Bu pencereyi kapatabilirsiniz.
timeout /t 3
'@
Set-Content -Path (Join-Path $PkgDir "Durdur.bat") -Value $durdurBat -Encoding ascii

# 7.3) VC++ Redistributable kopyala - portable kullanimda manuel kurulabilsin diye
Copy-Item $VcRedistPath (Join-Path $PkgDir "vc_redist.x64.exe") -Force

# ---------------------------------------------------------------------------
# 8) Kisa Turkce Benioku
# ---------------------------------------------------------------------------
$readme = @"
KAMERA YONETIMI SISTEMI - MUSTERI PAKETI
==========================================

Kurulum ve Kullanim Secenekleri:

Secenek A) Dogrudan Kurulum Sihirbazi (KameraYonetimi_Kurulum.exe varsa):
1. "KameraYonetimi_Kurulum.exe" dosyasini calistirin ve adimlari takip edin.
2. Masaustundeki kisayola cift tiklayarak sistemi baslatin.

Secenek B) Tasinabilir (Portable) Klasor Kullanimi:
1. Bu klasoru komple musteri bilgisayarina kopyalayin.
2. "DLL load failed" veya "Belirtilen modul bulunamadi" hatasi alirsaniz klasor icindeki "vc_redist.x64.exe" dosyasini kurun.
3. "Calistir.bat" dosyasina cift tiklayarak baslatin.

Genel Bilgiler:
- Tarayicida otomatik olarak http://localhost:8090 acilir.
- Ilk giris: admin / $InitialAdminPassword
- Guvenlik icin ilk giriste bu parola degistirilmelidir.
- Sistem musteri bilgisayarinda internet baglantisi gerektirmeden calisir.
- Sunucuyu kapatmak icin komut penceresini kapatabilir veya "Durdur.bat" dosyasini calistirabilirsiniz.
"@
Set-Content -Path (Join-Path $PkgDir "BENIOKU.txt") -Value $readme -Encoding ascii

# ---------------------------------------------------------------------------
# 9) Zip'le (kolay tasima icin)
# ---------------------------------------------------------------------------
Write-Host "==> Paket zip'leniyor (hata toleransli)..." -ForegroundColor Cyan
$ZipPath = Join-Path $OutDir "KameraYonetimi_Musteri_Paketi.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
try {
    if (Get-Command tar -ErrorAction SilentlyContinue) {
        Push-Location $OutDir
        try {
            & tar.exe -a -c -f "KameraYonetimi_Musteri_Paketi.zip" "KameraYonetimi"
            if ($LASTEXITCODE -ne 0) { throw "tar.exe hata kodu verdi: $LASTEXITCODE" }
        } finally {
            Pop-Location
        }
    } else {
        Compress-Archive -Path $PkgDir -DestinationPath $ZipPath -CompressionLevel Fastest
    }
    Write-Host "==> Zip paketi başarıyla oluşturuldu." -ForegroundColor Green
} catch {
    Write-Host "[UYARI] Zip paketi oluşturulamadı: $_" -ForegroundColor Yellow
    Write-Host "Inno Setup kurulum dosyası (.exe) bu durumdan etkilenmez." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 10) Inno Setup Derleme (Kurulum Exe Sihirbazi)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "==> Inno Setup Derleme kontrol ediliyor..." -ForegroundColor Cyan

# Bilinen ISCC.exe yollarını kontrol et
$IsccPaths = @(
    "C:\Users\kazim\AppData\Local\Programs\Inno Setup 60\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    "C:\Program Files\Inno Setup 5\ISCC.exe"
)

$IsccExe = $null
foreach ($path in $IsccPaths) {
    if (Test-Path $path) {
        $IsccExe = $path
        break
    }
}

# PATH icinde ara (eger kurulup PATH'e eklenmisse)
if (-not $IsccExe) {
    $IsccExe = Get-Command "iscc" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}

if ($IsccExe) {
    Write-Host "==> Inno Setup bulundu: $IsccExe" -ForegroundColor Green
    Write-Host "==> Kurulum paketi derleniyor (KameraYonetimi_Kurulum.exe)..." -ForegroundColor Cyan
    $InnoStageRoot = Join-Path $env:TEMP "KameraYonetimiInnoStage"
    $InnoPkgDir = Join-Path $InnoStageRoot "KameraYonetimi"
    $InnoVcRedistPath = Join-Path $InnoStageRoot "vc_redist.x64.exe"
    $InnoIssPath = Join-Path $InnoStageRoot "setup.iss"
    $InnoExePath = Join-Path $InnoStageRoot "KameraYonetimi_Kurulum.exe"
    $FinalInnoExePath = Join-Path $OutDir "KameraYonetimi_Kurulum.exe"

    if (Test-Path $InnoStageRoot) { Remove-Item $InnoStageRoot -Recurse -Force }
    New-Item -ItemType Directory -Path $InnoStageRoot -Force | Out-Null
    robocopy $PkgDir $InnoPkgDir /E /NFL /NDL /NJH /NJS /NC /NS | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Inno staging kopyalama hatasi (robocopy kod: $LASTEXITCODE)" }
    Copy-Item $VcRedistPath $InnoVcRedistPath -Force
    Copy-Item (Join-Path $RepoRoot "scripts\setup.iss") $InnoIssPath -Force

    $InnoLogPath = Join-Path $CacheDir "inno-package.log"
    $InnoErrPath = Join-Path $CacheDir "inno-package.err.log"
    $InnoTimeoutSeconds = 900
    if ($env:PACKAGE_INNO_TIMEOUT_SECONDS) {
        $parsedInnoTimeout = 0
        if ([int]::TryParse($env:PACKAGE_INNO_TIMEOUT_SECONDS, [ref]$parsedInnoTimeout) -and $parsedInnoTimeout -gt 0) {
            $InnoTimeoutSeconds = $parsedInnoTimeout
        }
    }
    $InnoArgs = @(
        "/Q",
        "/DPackageSource=$InnoPkgDir",
        "/DPackageOutput=$InnoStageRoot",
        "/DVcRedistSource=$InnoVcRedistPath",
        $InnoIssPath
    )
    function Quote-ProcessArgument([string]$Value) {
        if ($Value -match '^[A-Za-z0-9_./:=\\-]+$') { return $Value }
        return '"' + ($Value -replace '"', '\"') + '"'
    }
    $InnoStartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $InnoStartInfo.FileName = $IsccExe
    $InnoStartInfo.Arguments = ($InnoArgs | ForEach-Object { Quote-ProcessArgument $_ }) -join " "
    $InnoStartInfo.UseShellExecute = $false
    $InnoStartInfo.RedirectStandardOutput = $true
    $InnoStartInfo.RedirectStandardError = $true
    $InnoStartInfo.CreateNoWindow = $true
    $InnoProcess = New-Object System.Diagnostics.Process
    $InnoProcess.StartInfo = $InnoStartInfo
    [void]$InnoProcess.Start()
    $InnoStdoutTask = $InnoProcess.StandardOutput.ReadToEndAsync()
    $InnoStderrTask = $InnoProcess.StandardError.ReadToEndAsync()
    if (-not $InnoProcess.WaitForExit($InnoTimeoutSeconds * 1000)) {
        Write-Host "[UYARI] Inno Setup $InnoTimeoutSeconds saniye icinde tamamlanmadi; zip paketi teslim icin hazir." -ForegroundColor Yellow
        Write-Host "        Ayrinti: scripts\cache\inno-package.log" -ForegroundColor Yellow
        try { Stop-Process -Id $InnoProcess.Id -Force -ErrorAction Stop } catch {}
        try { $InnoProcess.WaitForExit() } catch {}
        Set-Content -Path $InnoLogPath -Value $InnoStdoutTask.Result -Encoding utf8
        Set-Content -Path $InnoErrPath -Value $InnoStderrTask.Result -Encoding utf8
        if (Test-Path $InnoExePath) {
            Copy-Item $InnoExePath $FinalInnoExePath -Force
            Write-Host "==> Mevcut kurulum programi hedefe kopyalandi." -ForegroundColor Yellow
        }
    } elseif ($InnoProcess.ExitCode -ne 0) {
        Set-Content -Path $InnoLogPath -Value $InnoStdoutTask.Result -Encoding utf8
        Set-Content -Path $InnoErrPath -Value $InnoStderrTask.Result -Encoding utf8
        Write-Host "[UYARI] Inno Setup derleme sirasinda hata verdi." -ForegroundColor Yellow
        Write-Host "        Ayrinti: scripts\cache\inno-package.log" -ForegroundColor Yellow
    } else {
        Set-Content -Path $InnoLogPath -Value $InnoStdoutTask.Result -Encoding utf8
        Set-Content -Path $InnoErrPath -Value $InnoStderrTask.Result -Encoding utf8
        Copy-Item $InnoExePath $FinalInnoExePath -Force
        Write-Host "==> Kurulum programi basariyla uretildi!" -ForegroundColor Green
        Write-Host "    Dosya: customer_package\KameraYonetimi_Kurulum.exe" -ForegroundColor Green
    }
} else {
    Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow
    Write-Host "[BILGI] Inno Setup (ISCC.exe) bilgisayarinizda bulunamadi." -ForegroundColor Yellow
    Write-Host "Eger sihirbazli tek tik kurulum paketi (.exe) uretmek istiyorsaniz:" -ForegroundColor Yellow
    Write-Host "1. https://jrsoftware.org/isdl.php adresinden Inno Setup 6'yi indirin ve kurun." -ForegroundColor Yellow
    Write-Host "2. Bu scripti tekrar calistirdiginizda otomatik olarak bulup KameraYonetimi_Kurulum.exe uretecektir." -ForegroundColor Yellow
    Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==> Paketleme islemleri tamamlandi!" -ForegroundColor Green
Write-Host "    Klasor : $PkgDir"
Write-Host "    Zip    : $ZipPath"
Write-Host ""
