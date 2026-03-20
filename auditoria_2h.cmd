@echo off
setlocal
cd /d "%~dp0"

echo ======================================
echo   VIDEO IA - AUDITORIA 2H
echo ======================================
echo.

powershell -ExecutionPolicy Bypass -File ".\scripts\start_2h_audit.ps1"
if errorlevel 1 (
  echo.
  echo Error al lanzar auditoria 2h.
  pause
  exit /b 1
)

echo.
echo Auditoria lanzada en segundo plano.
echo Para ver estado:
echo powershell -ExecutionPolicy Bypass -File ".\scripts\check_2h_audit.ps1"
pause
endlocal
