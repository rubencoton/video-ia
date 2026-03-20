@echo off
setlocal
cd /d "%~dp0"

echo ======================================
echo   VIDEO IA - PREPARACION AUTOMATICA
echo ======================================
echo.

powershell -ExecutionPolicy Bypass -File ".\scripts\setup_remote.ps1"
if errorlevel 1 (
  echo.
  echo Hubo un error en la preparacion automatica.
  pause
  exit /b 1
)

echo.
echo Todo listo.
echo Puedes abrir la app con VIDEO IA del escritorio.
pause
endlocal
