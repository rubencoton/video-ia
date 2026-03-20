$ErrorActionPreference = "Stop"

$repoPath = Split-Path -Parent $PSScriptRoot
Set-Location $repoPath

Write-Host "==============================="
Write-Host " VIDEO IA - SETUP AUTOMATICO"
Write-Host "==============================="
Write-Host ""

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env" -Force
    Write-Host "Creado .env desde .env.example"
}

$envContent = Get-Content ".env" -Raw -Encoding UTF8
$runwayKey = ""
if ($envContent -match "(?m)^RUNWAY_API_KEY=(.*)$") {
    $runwayKey = $Matches[1].Trim()
} else {
    $envContent = $envContent.TrimEnd() + "`r`nRUNWAY_API_KEY=`r`n"
}

if ($envContent -notmatch "(?m)^OPENAI_API_KEY=") {
    $envContent = $envContent.TrimEnd() + "`r`nOPENAI_API_KEY=`r`n"
}

$targetBackend = "local"
if (-not [string]::IsNullOrWhiteSpace($runwayKey)) {
    $targetBackend = "auto"
}

if ($envContent -notmatch "(?m)^VIDEO_GEN_BACKEND=") {
    $envContent = $envContent.TrimEnd() + "`r`nVIDEO_GEN_BACKEND=$targetBackend`r`n"
} else {
    $envContent = [regex]::Replace($envContent, "(?m)^VIDEO_GEN_BACKEND=.*$", "VIDEO_GEN_BACKEND=$targetBackend")
}
Set-Content ".env" $envContent -Encoding UTF8
if ($targetBackend -eq "auto") {
    Write-Host "Backend configurado en AUTO (Runway + respaldo local)."
} else {
    Write-Host "Backend configurado en LOCAL (sin cuentas)."
}

python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Fallo instalando dependencias."
}
Write-Host "Dependencias instaladas."

powershell -ExecutionPolicy Bypass -File ".\scripts\create_desktop_shortcut.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo crear acceso directo."
}
Write-Host "Acceso directo de escritorio creado."

Write-Host ""
Write-Host "Setup terminado. Ya puedes abrir VIDEO IA desde el escritorio."
