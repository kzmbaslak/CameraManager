# Windows gorev zamanlayicisina uretim calistiricisi kaydeder.
param(
    [string]$TaskName = "KameraYonetimiBackend",
    [string]$BackendDir = (Join-Path $PSScriptRoot "..\backend"),
    [string]$ListenHost = "0.0.0.0",
    [int]$Port = 8090,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ResolvedBackendDir = (Resolve-Path $BackendDir).Path
$RunScript = Join-Path $RepoRoot "scripts\run-service.ps1"

if (-not (Test-Path $RunScript)) {
    throw "Calistirici script bulunamadi: $RunScript"
}

$Arguments = @(
    '-NoProfile'
    '-ExecutionPolicy'
    'Bypass'
    '-File'
    ('"{0}"' -f $RunScript)
    '-BackendDir'
    ('"{0}"' -f $ResolvedBackendDir)
    '-ListenHost'
    ('"{0}"' -f $ListenHost)
    '-Port'
    $Port
) -join ' '

if ($ValidateOnly) {
    Write-Host "Planlanan task: $TaskName"
    Write-Host "Komut: powershell.exe $Arguments"
    exit 0
}

$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $Arguments -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$Principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$Description = 'Kamera yonetimi backend servisini Windows acilisinda calistirir.'

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description $Description -Force | Out-Null
Write-Host "Gorev kaydedildi: $TaskName"
