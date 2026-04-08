$repoPath = Split-Path -Parent $PSScriptRoot
$desktopPath = [Environment]::GetFolderPath("Desktop")

$canonicalName = "SEEDANCE RUBEN COTON.lnk"
$canonicalPath = Join-Path $desktopPath $canonicalName
$launcherPath = Join-Path $repoPath "iniciar_seedance_ruben_coton.cmd"

$legacyNames = @(
    "SEEDANCE RUBEN COTON CERO.lnk",
    "VIDEO IA.lnk"
)

if (-not (Test-Path $launcherPath)) {
    Write-Error "No existe el lanzador principal: $launcherPath"
    exit 1
}

$wshShell = New-Object -ComObject WScript.Shell

# Crear o corregir acceso directo canonico.
$shortcut = $wshShell.CreateShortcut($canonicalPath)
$shortcut.TargetPath = $launcherPath
$shortcut.WorkingDirectory = $repoPath
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,167"
$shortcut.Description = "Abrir SEEDANCE RUBEN COTON (app web local)"
$shortcut.Save()

$backupRoot = Join-Path $desktopPath "ACCESOS_DIRECTOS_RESPALDO_SEEDANCE"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $backupRoot $stamp
New-Item -Path $backupDir -ItemType Directory -Force | Out-Null

$moved = @()
foreach ($name in $legacyNames) {
    $oldPath = Join-Path $desktopPath $name
    if (Test-Path $oldPath) {
        $dest = Join-Path $backupDir $name
        Move-Item -Path $oldPath -Destination $dest -Force
        $moved += $dest
    }
}

Write-Host "ACCESO_DIRECTO_CANONICO: $canonicalPath"
if ($moved.Count -gt 0) {
    Write-Host "DUPLICADOS_MOVIDOS_A_RESPALDO:"
    $moved | ForEach-Object { Write-Host $_ }
} else {
    Write-Host "No se detectaron duplicados para mover."
}
Write-Host "RESPALDO: $backupDir"
