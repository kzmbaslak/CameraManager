# Windows gorev zamanlayicisindan gunluk alarm operasyon raporunu kaldirir.
param(
    [string]$TaskName = "KameraYonetimiAlarmReport",
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'

if ($ValidateOnly) {
    Write-Host "Kaldirilacak task: $TaskName"
    exit 0
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "Task bulunamadi: $TaskName"
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Alarm rapor gorevi kaldirildi: $TaskName"
