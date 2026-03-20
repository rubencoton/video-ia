# Setup inicial

## Requisitos

- Windows
- Python 3.10 o superior
- Pip

## Primer arranque

1. Abrir `iniciar_video_ia.cmd`.
2. Esperar instalacion automatica de dependencias.
3. Usar la ventana de la app.

## Crear icono en escritorio

Ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_desktop_shortcut.ps1
```

## Donde se guardan los resultados

- Cada trabajo se guarda en `output/job_YYYYMMDD_HHMMSS`.
- Dentro tendras:
  - `video_resultado.mp4`
  - `prompt.txt`
  - `resumen.json`
