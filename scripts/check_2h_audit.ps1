$ErrorActionPreference = "Stop"

$repoPath = Split-Path -Parent $PSScriptRoot
$reportsDir = Join-Path $repoPath "reports"
$pidFile = Join-Path $reportsDir "audit_2h_latest.pid"
$metaFile = Join-Path $reportsDir "audit_2h_latest.txt"

if (-not (Test-Path $pidFile)) {
    Write-Host "No hay auditoria 2h lanzada."
    exit 0
}

$pidText = (Get-Content $pidFile -Raw -Encoding UTF8).Trim()
if (-not $pidText) {
    Write-Host "PID vacio en archivo de auditoria."
    exit 0
}

$auditPid = [int]$pidText
$proc = Get-Process -Id $auditPid -ErrorAction SilentlyContinue

if ($proc) {
    Write-Host "Auditoria en ejecucion. PID: $auditPid"
} else {
    Write-Host "Auditoria finalizada. PID: $auditPid"
}

if (Test-Path $metaFile) {
    Write-Host ""
    Write-Host "Detalle:"
    Get-Content $metaFile -Encoding UTF8 | ForEach-Object { Write-Host $_ }
}
