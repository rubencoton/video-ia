# Setup inicial

## Requisitos

- Windows
- Python 3.10 o superior
- Pip

## Primer arranque

1. Abrir `iniciar_video_ia.cmd`.
2. Esperar instalacion automatica de dependencias.
3. Se abrira la app en navegador local.

## Uso rapido

1. Sube video + imagen + prompt.
2. Pulsa `Generar video`.
3. En el preview (derecha), pausa en el segundo exacto.
4. Haz click o arrastra para marcar zona.
5. En el chat (izquierda), habla con la IA usando esas marcas.

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

## Notas

- Si pones `OPENAI_API_KEY` en `.env`, el chat puede responder con IA online.
- Si no hay API key, el chat funciona en modo local guiado.
