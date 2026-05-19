# cv-colegios

Herramienta semi-automática para personalizar y enviar la hoja de vida a colegios privados de Bogotá, Antioquia y Barranquilla.

A partir del directorio público del MEN, el pipeline:

1. **Descubre** colegios y los almacena en SQLite.
2. **Enriquece** cada colegio buscando su sitio web y correo de contacto, y clasificando su perfil pedagógico (bilingüe, IB, religioso, etc.) con Claude.
3. **Genera** una versión personalizada del CV (DOCX → PDF) y una carta de presentación por colegio, usando los prompts de `prompts/` y validando contra alucinaciones.
4. **Envía** los borradores a Gmail vía OAuth para que el usuario los revise y mande con un click.

## Stack

- Python 3.14 · SQLite · python-docx · LibreOffice (DOCX→PDF)
- Anthropic API (`claude-sonnet-4-6`) con prompt caching
- Brave Search API para descubrir sitios web
- Gmail API (OAuth Desktop App) para borradores

## Estructura

```
modulos/          # pipeline (descubrir, enriquecer, generar, enviar, ...)
prompts/          # plantillas de prompts para Claude
scripts/debug/    # scripts auxiliares de diagnóstico y reproducción
tests/            # suite de pytest
docs/             # diseño y especificaciones
config/.env.example
```

## Uso

```powershell
# Una sola vez: autorizar Gmail
.\.venv\Scripts\python.exe autorizar_gmail.py

# Pipeline por colegio
.\.venv\Scripts\python.exe correr_modulo.py descubrir
.\.venv\Scripts\python.exe correr_modulo.py enriquecer --max 50
.\.venv\Scripts\python.exe correr_modulo.py generar       --max 5
.\.venv\Scripts\python.exe correr_modulo.py enviar_borradores
```

Diseño completo en `docs/superpowers/specs/2026-05-05-cv-colegios-design.md`.

## Datos sensibles

`config/.env`, `data/colegios.db`, el CV base y la plantilla DOCX no se versionan (ver `.gitignore`). Para correr el proyecto se necesitan:

- `config/.env` con `ANTHROPIC_API_KEY`, `BRAVE_API_KEY`
- `config/credentials.json` (OAuth Desktop Gmail)
- `data/cv_base.docx` (CV original del usuario)
