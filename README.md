# SEEDANCE RUBEN COTON (APLICACIÓN ÚNICA)

Aplicación local unificada con dos modos en una sola interfaz:

1. `VIDEO IA`: edición de vídeo subido (vídeo + imagen + audio + chat + marcas)
2. `SIDANCE local`: texto a vídeo en local (sin API externa de pago)

## Base de fusión

- Aplicación A (base): `video-ia`
- Aplicación B integrada: `SEEDANCE/APP_LOCAL_CERO` (Zidans/Sidance local)

La fusión se hizo sobre la aplicación A para conservar todo lo que ya funcionaba en VIDEO IA.

## Funciones disponibles

### VIDEO IA (flujo original conservado)

- Subida de vídeo, imagen y audio opcionales
- Texto de instrucción libre
- Texto superpuesto configurable (posición, tamaño y color)
- Vista previa del resultado
- Chat IA contextual
- Marcas por tiempo y posición (punto y rectángulo)
- Exportación JSON de marcas
- Salida fija Reels `1080x1920` para este modo
- Soporte de composición completa: `video + imagen + audio + texto + prompt`
- Si subes solo imagen, la app crea vídeo base y aplica prompt + audio + texto

### SIDANCE local (nuevo flujo integrado)

- Texto a vídeo local
- Modelo local por defecto: `THUDM/CogVideoX1.5-5B`
- Parámetros editables: calidad, pasos, guía de ajuste y semilla
- Sin uso de API de pago para este modo

## Arranque rápido

1. Ejecuta `iniciar_seedance_ruben_coton.cmd`
2. Se abre en `http://127.0.0.1:7860` (o puerto libre cercano)
3. En la izquierda eliges modo:
   - `VIDEO IA (editar vídeo subido)`
   - `SIDANCE local (texto a vídeo)`

## Dependencias

### Mínimas (siempre)

Instaladas por `iniciar_video_ia.cmd`:

- `Flask`
- `imageio-ffmpeg`

### Extra para SIDANCE local

Instala una vez si quieres activar texto a vídeo local:

```bash
pip install -r requirements_sidance_local.txt
```

Notas:
- Requiere GPU NVIDIA con CUDA para generar con SIDANCE local.
- La primera ejecución del modelo descarga pesos (archivo grande).

## Variables de entorno

Archivo base: `.env.example`

Variables relevantes:

- `VIDEO_GEN_BACKEND=auto|runway|local`
- `RUNWAY_API_KEY=...` (solo si quieres modo nube)
- `SIDANCE_LOCAL_MODEL=THUDM/CogVideoX1.5-5B`
- `SIDANCE_LOCAL_STEPS=28`
- `SIDANCE_LOCAL_GUIDANCE=6.0`
- `SIDANCE_LOCAL_NUM_FRAMES=49`
- `SIDANCE_LOCAL_FPS=16`

## Scripts útiles

- `iniciar_seedance_ruben_coton.cmd` -> lanzador principal
- `iniciar_video_ia.cmd` -> lanzador compatible anterior
- `preparar_video_ia_remoto.cmd` -> preparación local base
- `scripts/normalizar_accesos_directos_seedance.ps1` -> deja un solo acceso directo y guarda duplicados en respaldo

## Estructura

```text
video-ia/
|- src/
|  |- app.py
|  |- web_app.py
|  |- video_composer.py
|  |- video_processor.py
|  |- sidance_local.py
|  `- static/
|     |- index.html
|     |- app.js
|     `- styles.css
|- requirements.txt
|- requirements_sidance_local.txt
|- iniciar_video_ia.cmd
`- iniciar_seedance_ruben_coton.cmd
```

---

## CIERRE DE ENTORNO LOCAL (MIGRACION)

- Fecha de cierre: 2026-04-08 15:24:45
- Estado: preparado para migrar a nuevo PC/sistema cloud.
- Repositorio: sincronizado con GitHub en la rama activa.
- Nota: este proyecto queda listo para retomar desde otro equipo clonando el repo.

### CHECKLIST RAPIDA

- [x] Codigo versionado en GitHub.
- [x] README actualizado para traspaso.
- [x] Trabajo local preparado para cierre.


<!-- CIERRE_MIGRACION_2026_04_08 -->
## Cierre de migracion (2026-04-08)
- Estado: preparado para mover a nuevo PC/sistema cloud.
- Fecha de cierre: 
2026-04-08 15:25:38 +02:00
- Rama activa: 
main
- Nota: cambios subidos a GitHub para reanudar desde otro entorno.



## CIERRE CLOUD (2026-04-08)

- Estado: repositorio preparado para migracion a nuevo sistema.
- Ultimo cierre tecnico: 2026-04-08 (Europe/Madrid).
- Siguiente uso recomendado: clonar desde GitHub y continuar en la rama actual.


## CIERRE MIGRACION CLOUD

- Fecha: 2026-04-08
- Estado: preparado para retomar desde nuevo sistema

