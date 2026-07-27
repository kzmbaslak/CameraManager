# Windows gorev zamanlayicisina gunluk alarm operasyon raporu kaydeder.
param(
    [string]$TaskName = "KameraYonetimiAlarmReport",
    [string]$BackendDir = (Join-Path $PSScriptRoot "..\backend"),
    [string]$At = "03:15",
    [int]$WindowHours = 24,
    [int]$RetentionDays = 180,
    [int]$KeepLatest = 30,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ResolvedBackendDir = (Resolve-Path $BackendDir).Path
$RunScript = Join-Path $RepoRoot "scripts\run-alarm-report.ps1"

if (-not (Test-Path $RunScript)) {
    throw "Alarm rapor calistirici script bulunamadi: $RunScript"
}

$Arguments = @(
    '-NoProfile'
    '-ExecutionPolicy'
    'Bypass'
    '-File'
    ('"{0}"' -f $RunScript)
    '-BackendDir'
    ('"{0}"' -f $ResolvedBackendDir)
    '-WindowHours'
    $WindowHours
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
$Description = 'Kamera yonetimi alarm operasyon raporunu gunluk uretir.'

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description $Description -Force | Out-Null
Write-Host "Alarm rapor gorevi kaydedildi: $TaskName"
