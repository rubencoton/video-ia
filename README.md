# VIDEO IA

App local para Windows que permite:

- subir un video
- subir una imagen de referencia
- escribir un prompt
- generar un video de salida en `output/`

## Como abrir la app

1. Doble clic en `iniciar_video_ia.cmd`.
2. Se abre la ventana `VIDEO IA - App Local`.
3. Cargas video + imagen + prompt.
4. Pulsa `Generar video`.

## Acceso directo de escritorio

Para crear el icono en el escritorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_desktop_shortcut.ps1
```

Se creara `VIDEO IA.lnk` en el escritorio.

## Efectos de prompt detectados (v1)

La app detecta palabras del prompt y aplica filtros automaticos:

- `blanco y negro`
- `sepia` o `vintage`
- `mas brillo`
- `contraste`
- `cinematic`

Si no detecta una palabra conocida, genera video con la imagen de referencia superpuesta.

## Estructura

```
video-ia/
|- assets/
|- docs/
|- input/
|- output/
|- scripts/
|- src/
|  |- app.py
|  `- video_processor.py
|- iniciar_video_ia.cmd
|- requirements.txt
|- .gitignore
|- LICENSE
`- README.md
```
