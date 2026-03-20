param(
    [int]$DurationMinutes = 120,
    [int]$IntervalSeconds = 300
)

$ErrorActionPreference = "Stop"

$repoPath = Split-Path -Parent $PSScriptRoot
Set-Location $repoPath

$reportsDir = Join-Path $repoPath "reports"
if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = Join-Path $reportsDir "audit_2h_$stamp.md"
$jsonlPath = Join-Path $reportsDir "audit_2h_$stamp.jsonl"
$stdoutPath = Join-Path $reportsDir "audit_2h_$stamp.stdout.log"
$stderrPath = Join-Path $reportsDir "audit_2h_$stamp.stderr.log"
$pidFile = Join-Path $reportsDir "audit_2h_latest.pid"
$metaFile = Join-Path $reportsDir "audit_2h_latest.txt"

$args = @(
    "scripts\run_functional_audit.py",
    "--duration-minutes", "$DurationMinutes",
    "--interval-seconds", "$IntervalSeconds",
    "--force-local",
    "--report", "`"$reportPath`"",
    "--jsonl", "`"$jsonlPath`""
)

$process = Start-Process `
    -FilePath "python" `
    -ArgumentList $args `
    -WorkingDirectory $repoPath `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath

Set-Content -Path $pidFile -Value $process.Id -Encoding UTF8
@(
    "PID=$($process.Id)"
    "REPORT=$reportPath"
    "JSONL=$jsonlPath"
    "STDOUT=$stdoutPath"
    "STDERR=$stderrPath"
    "STARTED=$(Get-Date -Format o)"
) | Set-Content -Path $metaFile -Encoding UTF8

Write-Host "Auditoria 2h lanzada."
Write-Host "PID: $($process.Id)"
Write-Host "Reporte: $reportPath"
Write-Host "Log: $jsonlPath"
