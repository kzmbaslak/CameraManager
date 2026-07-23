# Kayitli gorevin durumunu ve calisma anlik ozetini dondurur.
param(
    [string]$TaskName = "KameraYonetimiBackend"
)

$ErrorActionPreference = 'Stop'

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "Task bulunamadi: $TaskName"
    exit 0
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName
[pscustomobject]@{
    TaskName = $task.TaskName
    State = $task.State
    LastRunTime = $info.LastRunTime
    LastTaskResult = $info.LastTaskResult
    NextRunTime = $info.NextRunTime
    NumberOfMissedRuns = $info.NumberOfMissedRuns
} | Format-List
