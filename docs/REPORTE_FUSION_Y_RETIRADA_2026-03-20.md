# REPORTE DE FUSIÓN Y RETIRADA CONTROLADA

Fecha: 2026-03-20

## Estado general

- Fusión: COMPLETADA
- Validación técnica: APTO
- Copia de seguridad de la aplicación antigua: CREADA
- Borrado destructivo de la aplicación antigua: PENDIENTE (requiere confirmación final)

## Archivos fusionados (aplicación única)

- `src/sidance_local.py` (nuevo)
- `src/web_app.py` (integración de rutas API de SIDANCE)
- `src/static/index.html` (selector de modo unificado)
- `src/static/app.js` (lógica unificada VIDEO IA + SIDANCE local)
- `src/static/styles.css` (controles nuevos)
- `.env.example` (variables SIDANCE)
- `requirements_sidance_local.txt` (dependencias opcionales SIDANCE)
- `iniciar_video_ia.cmd` (nombre y nota de activación SIDANCE)
- `iniciar_seedance_ruben_coton.cmd` (nuevo lanzador principal)
- `README.md` (documentación unificada)

## Validación APTO/NO APTO

- `python -m compileall src` -> APTO
- `GET /api/system-status` -> APTO
- `POST /api/chat` -> APTO
- `POST /api/generate` sin vídeo (control de error) -> APTO
- `POST /api/generate-sidance` con texto vacío (control de error) -> APTO

Nota:
- Generación SIDANCE real no se ejecutó en esta validación porque depende de GPU CUDA y pesos de modelo.

## Copia de seguridad

Copia de seguridad realizada de aplicación antigua (sin `.venv_local_cero`):

- `backups/APP_LOCAL_CERO_snapshot_20260320_125358`

## Riesgos residuales

1. SIDANCE local necesita GPU NVIDIA CUDA para generar vídeo.
2. Primera carga del modelo puede tardar por descarga de pesos.
3. Si faltan dependencias SIDANCE, el modo aparece no disponible hasta instalar `requirements_sidance_local.txt`.

## Vuelta atrás (rápida)

1. Usar estado git anterior en `video-ia` (commit previo a fusión).
2. Recuperar aplicación antigua desde copia de seguridad:
   - `backups/APP_LOCAL_CERO_snapshot_20260320_125358`
3. Reusar lanzador anterior de `SEEDANCE/APP_LOCAL_CERO` si hiciera falta.

## Plan de retirada destructiva (pendiente confirmación)

Cuando se confirme:

1. Eliminar carpeta antigua:
   - `C:\Users\elrub\Desktop\CARPETA CODEX\01_PROYECTOS\SEEDANCE\APP_LOCAL_CERO`
2. Limpiar scripts no usados en repo antiguo SEEDANCE.
3. Actualizar README final de SEEDANCE como "obsoleto por fusión".
