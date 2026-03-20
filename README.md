# VIDEO IA

Repositorio base para construir un flujo de generacion de video con:

- un video original (movimiento base)
- una imagen de referencia
- un prompt de texto

## Objetivo

Crear una pipeline clara para transformar un video de entrada en un video final editado con IA.

## Estructura inicial

```
video-ia/
|- assets/          # Recursos visuales del proyecto
|- docs/            # Documentacion y plan de trabajo
|- input/           # Archivos de entrada (video, imagen, prompt)
|- output/          # Resultados generados
|- src/             # Codigo del proyecto
|- .env.example     # Variables de entorno de ejemplo
|- .gitignore
|- LICENSE
`- README.md
```

## Flujo de trabajo (v1)

1. Copiar el video base en `input/video.mp4`.
2. Copiar la imagen de referencia en `input/referencia.png`.
3. Escribir el prompt en `input/prompt.txt`.
4. Ejecutar el script de generacion (pendiente en `src/`).
5. Revisar el resultado en `output/`.

## Estado

Este repo queda preparado para empezar la implementacion tecnica.
