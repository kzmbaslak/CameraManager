# Windows gorev zamanlayicisina gunluk sistem yedegi kaydeder.
param(
    [string]$TaskName = "KameraYonetimiBackup",
    [string]$BackendDir = (Join-Path $PSScriptRoot "..\backend"),
    [string]$At = "03:00",
    [int]$RetentionDays = 30,
    [int]$KeepLatest = 7,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ResolvedBackendDir = (Resolve-Path $BackendDir).Path
$RunScript = Join-Path $RepoRoot "scripts\run-backup.ps1"

if (-not (Test-Path $RunScript)) {
    throw "Yedek calistirici script bulunamadi: $RunScript"
}

$Arguments = @(
    '-NoProfile'
    '-ExecutionPolicy'
    'Bypass'
    '-File'
    ('"{0}"' -f $RunScript)
    '-BackendDir'
    ('"{0}"' -f $ResolvedBackendDir)
    '-RetentionDays'
    $RetentionDays
    '-KeepLatest'
    $KeepLatest
) -join ' '

$TriggerAt = [datetime]::ParseExact($At, 'HH:mm', $null)

if ($ValidateOnly) {
    Write-Host "Planlanan task: $TaskName"
    Write-Host "Saat: $($TriggerAt.ToString('HH:mm'))"
    Write-Host "Komut: powershell.exe $Arguments"
    exit 0
}

$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $Arguments -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerAt
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
$Principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$Description = 'Kamera yonetimi sistem yedegini gunluk alir ve eski arsivleri retention politikasina gore temizler.'

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description $Description -Force | Out-Null
Write-Host "Yedek gorevi kaydedildi: $TaskName"
