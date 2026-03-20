# VIDEO IA

App local para Windows que permite:

- subir un video
- subir una imagen de referencia (opcional)
- subir audio externo (opcional)
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

## Preparacion automatica (sin cuentas)

Si no tienes nada configurado, ejecuta:

1. `preparar_video_ia_remoto.cmd`
2. Ese script:
   - crea `.env`
   - pone backend en `local`
   - instala dependencias
   - crea acceso directo de escritorio

## Backend de generacion (calidad-precio)

- Modo por defecto: `VIDEO_GEN_BACKEND=auto`
- En `auto`, la app usa:
  - `Runway (gen4_aleph)` si hay `RUNWAY_API_KEY`
  - `Local (ffmpeg)` como respaldo si Runway no esta disponible
- Esto prioriza buena calidad con flujo practico para redes sociales.

Si no quieres cuentas por ahora:

- usa `VIDEO_GEN_BACKEND=local`
- todo funciona en tu PC sin API key

Nota importante de Runway API:

- Aunque tengas API key, Runway API puede pedir una primera compra de creditos
  para habilitar uploads por API.

## Audio en salida

- Si no subes audio externo:
  - se conserva el audio del video base
- Si subes audio externo:
  - se usa ese audio en el resultado final

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
