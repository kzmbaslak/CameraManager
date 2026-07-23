# Uretim arka plan calistiricisi; backend uvicorn islemini tek surecte baslatir.
param(
    [string]$BackendDir = (Join-Path $PSScriptRoot "..\backend"),
    [string]$ListenHost = "0.0.0.0",
    [int]$Port = 8090,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'

$ResolvedBackendDir = (Resolve-Path $BackendDir).Path
$PythonExe = Join-Path $ResolvedBackendDir "venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Python sanal ortami bulunamadi: $PythonExe"
}

if ($ValidateOnly) {
    Write-Host "Backend servis komutu hazir: $PythonExe -m uvicorn main:app --host $ListenHost --port $Port"
    exit 0
}

Set-Location $ResolvedBackendDir
& $PythonExe -m uvicorn main:app --host $ListenHost --port $Port
exit $LASTEXITCODE
