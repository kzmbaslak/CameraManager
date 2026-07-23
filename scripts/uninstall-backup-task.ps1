# Windows gorev zamanlayicisindan gunluk sistem yedegini kaldirir.
param(
    [string]$TaskName = "KameraYonetimiBackup",
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
Write-Host "Yedek gorevi kaldirildi: $TaskName"
