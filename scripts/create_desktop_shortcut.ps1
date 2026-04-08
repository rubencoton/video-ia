$normalizador = Join-Path $PSScriptRoot "normalizar_accesos_directos_seedance.ps1"
if (-not (Test-Path $normalizador)) {
    Write-Error "No existe el script normalizador: $normalizador"
    exit 1
}

powershell -ExecutionPolicy Bypass -File $normalizador
