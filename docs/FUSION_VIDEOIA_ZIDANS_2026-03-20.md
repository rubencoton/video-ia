# FUSIÓN VIDEO IA + ZIDANS (SIDANCE)

Fecha: 2026-03-20

## 1) Inventario técnico

### Aplicación A (base)

Ruta: `C:\Users\elrub\Desktop\CARPETA CODEX\01_PROYECTOS\video-ia`

- Servidor: Flask (`src/web_app.py`, `src/video_processor.py`)
- Interfaz web: HTML/CSS/JS (`src/static/*`)
- IA chat: `src/ai_chat.py`
- Entradas: `input/web_uploads`
- Salidas: `output/job_*`
- Dependencias base: `Flask`, `imageio-ffmpeg`
- Variables clave:
  - `VIDEO_GEN_BACKEND`
  - `RUNWAY_API_KEY`
  - `OPENAI_API_KEY`

### Aplicación B (Zidans / SIDANCE local)

Ruta tomada para fusión:
`C:\Users\elrub\Desktop\CARPETA CODEX\01_PROYECTOS\SEEDANCE\APP_LOCAL_CERO`

- Interfaz original: Gradio (`app_seedance_ruben_coton.py`)
- Motor: `diffusers` + `CogVideoXPipeline` + `torch` CUDA
- Dependencias pesadas:
  - `torch`, `torchvision`, `diffusers`, `transformers`, `accelerate`
  - `safetensors`, `sentencepiece`
- Variables clave:
  - `SEEDANCE_LOCAL_MODEL`
  - `SEEDANCE_LOCAL_STEPS`

## 2) Mapa de conflictos y compatibilidad

Conflictos detectados:

- Interfaz duplicada:
  - Aplicación A usa Flask+HTML
  - Aplicación B usa Gradio
- Puerto por defecto igual (`7860`)
- Nombre de aplicación diferente
- Dependencias de la aplicación B pesadas y opcionales

Compatibilidad:

- Ambos flujos son Python local
- Se puede integrar el motor SIDANCE en servidor Flask con carga perezosa
- Se puede mantener aplicación A intacta y sumar modo SIDANCE en la misma interfaz

## 3) Arquitectura final unificada

- Aplicación única: `video-ia` renombrada funcionalmente a `SEEDANCE RUBEN COTON`
- Servidor único Flask:
  - `/api/generate` -> flujo VIDEO IA original
  - `/api/generate-sidance` -> flujo SIDANCE local texto a vídeo
  - `/api/system-status` -> estado general + estado SIDANCE
- Interfaz web única:
  - Selector de modo (VIDEO IA / SIDANCE local)
  - Vista previa, chat y marcas comunes
- Dependencias:
  - Base en `requirements.txt`
  - SIDANCE opcional en `requirements_sidance_local.txt`

## 4) Plan de migración ejecutado

1. Crear módulo `src/sidance_local.py` con estado y generación local.
2. Integrar rutas API nuevas en `src/web_app.py`.
3. Actualizar interfaz para selector de modo en `src/static/index.html`.
4. Actualizar lógica de JavaScript para ambos flujos en `src/static/app.js`.
5. Ajustar estilos para nuevos controles en `src/static/styles.css`.
6. Unificar nombre de la aplicación y lanzadores.
7. Actualizar README y variables de entorno.

## 5) Riesgo / impacto

- Riesgo alto:
  - SIDANCE local requiere GPU CUDA + dependencias pesadas.
- Riesgo medio:
  - Primera carga de modelo tarda por descarga de pesos.
- Riesgo bajo:
  - Flujo VIDEO IA se mantiene con endpoint original sin cambios de comportamiento.
