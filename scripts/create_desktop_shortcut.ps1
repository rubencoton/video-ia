$repoPath = Split-Path -Parent $PSScriptRoot
$launcherPath = Join-Path $repoPath "iniciar_video_ia.cmd"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "VIDEO IA.lnk"

if (-not (Test-Path $launcherPath)) {
    Write-Error "No existe el lanzador: $launcherPath"
    exit 1
}

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcherPath
$shortcut.WorkingDirectory = $repoPath
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,167"
$shortcut.Description = "Abrir app local VIDEO IA"
$shortcut.Save()

Write-Host "Acceso directo creado en: $shortcutPath"
