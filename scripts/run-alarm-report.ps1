# Alarm operasyon raporunu tek sefer uretir ve retention politikasini uygular.
param(
    [string]$BackendDir = (Join-Path $PSScriptRoot "..\backend"),
    [int]$WindowHours = 24,
    [int]$RetentionDays = 180,
    [int]$KeepLatest = 30,
    [switch]$SkipCleanup,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'

$ResolvedBackendDir = (Resolve-Path $BackendDir).Path
$PythonExe = Join-Path $ResolvedBackendDir "venv\Scripts\python.exe"
$ReportScript = Join-Path $ResolvedBackendDir "scripts\export_alarm_report.py"

if (-not (Test-Path $PythonExe)) {
    throw "Python sanal ortami bulunamadi: $PythonExe"
}

if (-not (Test-Path $ReportScript)) {
    throw "Alarm rapor scripti bulunamadi: $ReportScript"
}

$ReportArgs = @(
    $ReportScript
    '--hours'
    $WindowHours
    '--retention-days'
    $RetentionDays
    '--keep-latest'
    $KeepLatest
)

if ($SkipCleanup) {
    $ReportArgs += '--skip-cleanup'
}

if ($ValidateOnly) {
    Write-Host "Alarm rapor komutu hazir: $PythonExe $($ReportArgs -join ' ')"
    exit 0
}

Set-Location $ResolvedBackendDir
& $PythonExe @ReportArgs
exit $LASTEXITCODE
