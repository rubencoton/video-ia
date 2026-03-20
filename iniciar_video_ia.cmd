@echo off
setlocal
cd /d "%~dp0"

echo ======================================
echo   VIDEO IA - INICIO LOCAL
echo ======================================
echo.

python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo No se pudieron instalar dependencias.
  echo Revisa tu conexion o Python/pip.
  pause
  exit /b 1
)

python src\app.py
if errorlevel 1 (
  echo.
  echo La app no pudo iniciarse correctamente.
  pause
  exit /b 1
)

endlocal
