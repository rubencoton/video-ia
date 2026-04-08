@echo off
setlocal
cd /d "%~dp0"

echo ======================================
echo   SEEDANCE RUBEN COTON - INICIO LOCAL
echo ======================================
echo.

python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo No se pudieron instalar dependencias.
  echo Revisa tu conexión o Python/pip.
  pause
  exit /b 1
)

if exist requirements_sidance_local.txt (
  echo.
  echo [INFO] Si quieres activar SIDANCE local:
  echo        pip install -r requirements_sidance_local.txt
)

python src\app.py
if errorlevel 1 (
  echo.
  echo La aplicación no pudo iniciarse correctamente.
  pause
  exit /b 1
)

endlocal
