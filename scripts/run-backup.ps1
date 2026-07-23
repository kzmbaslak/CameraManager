# Sistem yedegini tek sefer calistirir ve retention politikasini uygular.
param(
    [string]$BackendDir = (Join-Path $PSScriptRoot "..\backend"),
    [int]$RetentionDays = 30,
    [int]$KeepLatest = 7,
    [switch]$SkipCleanup,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'

$ResolvedBackendDir = (Resolve-Path $BackendDir).Path
$PythonExe = Join-Path $ResolvedBackendDir "venv\Scripts\python.exe"
$BackupScript = Join-Path $ResolvedBackendDir "scripts\backup_system.py"

if (-not (Test-Path $PythonExe)) {
    throw "Python sanal ortami bulunamadi: $PythonExe"
}

if (-not (Test-Path $BackupScript)) {
    throw "Yedek scripti bulunamadi: $BackupScript"
}

$BackupArgs = @(
    $BackupScript
    '--retention-days'
    $RetentionDays
    '--keep-latest'
    $KeepLatest
)

if ($SkipCleanup) {
    $BackupArgs += '--skip-cleanup'
}

if ($ValidateOnly) {
    Write-Host "Yedek komutu hazir: $PythonExe $($BackupArgs -join ' ')"
    exit 0
}

Set-Location $ResolvedBackendDir
& $PythonExe @BackupArgs
exit $LASTEXITCODE
