# VIDEO IA

App local para Windows que permite:

- subir un video
- subir una imagen de referencia
- escribir un prompt
- generar un video de salida en `output/`
- salida fija para Reels: `9:16` y `1080x1920`
- ver preview a la derecha
- chatear con IA a la izquierda
- marcar zonas del video por tiempo y posicion (punto o rectangulo)

## Como abrir la app

1. Doble clic en `iniciar_video_ia.cmd`.
2. Se abre en navegador `http://127.0.0.1:7860` (o puerto cercano).
3. Cargas video + imagen + prompt.
4. Pulsa `Generar video`.
5. Marca zonas en el preview y habla con la IA en el chat.

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

## Formato de salida fijo

- Todos los videos se exportan en `9:16` (vertical).
- Resolucion fija: `1080 x 1920`.
- Codificacion compatible: `H.264 + AAC`.

## Marcas en el video

- Haz click para crear marca de punto.
- Arrastra para crear marca rectangular.
- Cada marca guarda:
  - segundo exacto del video
  - posicion X/Y en porcentaje
  - tamano si es rectangulo
  - nota opcional
- Puedes exportar las marcas en JSON.

## Estructura

```
video-ia/
|- assets/
|- docs/
|- input/
|- output/
|- scripts/
|- src/
|  |- ai_chat.py
|  |- app.py
|  |- video_processor.py
|  |- web_app.py
|  `- static/
|     |- app.js
|     |- index.html
|     `- styles.css
|- iniciar_video_ia.cmd
|- requirements.txt
|- .gitignore
|- LICENSE
`- README.md
```
