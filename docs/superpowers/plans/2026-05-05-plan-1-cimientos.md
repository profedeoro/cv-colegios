# Plan 1 — Cimientos del proyecto y plantilla pulida

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar listos los cimientos del proyecto (estructura, BD SQLite con máquina de estados, validador anti-alucinación, motor de plantillas DOCX, conversor a PDF, cliente de Claude) y entregar el comando `reconstruir_plantilla.py` que produce la plantilla base pulida a partir del CV original.

**Architecture:** Proyecto Python modular con SQLite como única fuente de verdad. Cada módulo con una responsabilidad única, testeado con pytest siguiendo TDD (test rojo → implementación mínima → test verde → commit). Sin acoplamientos entre módulos: cada uno se puede leer y entender independientemente.

**Tech Stack:** Python 3.11+, SQLite (stdlib), pytest, python-docx, LibreOffice (headless), anthropic SDK, pdfplumber, python-dotenv.

**Spec referenciado:** `docs/superpowers/specs/2026-05-05-cv-colegios-design.md`

---

## Roadmap completo (contexto)

Este es el **Plan 1 de 5**. Cada plan termina con software ejecutable y testeado:

| Plan | Producto al terminar |
|---|---|
| **1. Cimientos (este)** | Plantilla DOCX pulida, BD inicializada, infraestructura testeada |
| 2. Descubrimiento + Enriquecimiento | Pipeline que encuentra y clasifica colegios |
| 3. Generación + Envío | Pipeline genera HV+carta y crea borradores en Gmail |
| 4. Respuestas + Seguimientos | Loop cerrado con detección y notificaciones |
| 5. Orquestación + Despliegue | Sistema completo con Programador de Windows |

---

## Conceptos clave para Daniel (5 minutos de lectura)

Si vas a implementar tú mismo (o con ayuda de Claude), conviene entender:

- **TDD (Test-Driven Development):** primero escribes una prueba que falla, luego escribes el código mínimo para que pase, después se ajusta. Garantiza que el código nace probado.
- **pytest:** la herramienta de Python para correr pruebas. `pytest tests/` corre todas. `pytest tests/test_db.py::test_insert -v` corre solo una y muestra detalle.
- **Commit frecuente:** después de cada tarea pequeña haces `git commit`. Si algo se rompe, vuelves al último commit con `git checkout .`.
- **Máquina de estados:** un colegio solo puede pasar de un estado válido a otro. Por ejemplo `descubierto → enriquecido` está bien, pero `enriquecido → descubierto` no. La BD lo bloquea con un trigger SQL.

---

## Tarea 0: Configurar tu entorno local (una sola vez, manual)

Esto se hace UNA vez en tu laptop. No es código, es setup.

- [ ] **Paso 1: Verificar que Python 3.11+ esté instalado**

```powershell
python --version
```

Si dice "3.11" o superior, sigue. Si no, instala desde https://www.python.org/downloads/ marcando la casilla "Add Python to PATH".

- [ ] **Paso 2: Verificar que LibreOffice esté instalado**

```powershell
& "C:\Program Files\LibreOffice\program\soffice.exe" --version
```

Si no está, descarga desde https://www.libreoffice.org/download/download-libreoffice/.

- [ ] **Paso 3: Configurar tu identidad de git localmente (solo en este repo, no global)**

Esto se hará en la Tarea 1 después de inicializar el repo. Por ahora, ten listos:
- Tu nombre: `Daniel Eduardo Villalba de Oro`
- Tu correo: `danedu348@gmail.com`

- [ ] **Paso 4: Tener tu API key de Anthropic**

Crea cuenta en https://console.anthropic.com, agrega $20 USD de saldo, crea una API key y guárdala en un lugar seguro (la usaremos en la Tarea 5).

---

## Tarea 1: Inicializar el repositorio git y el .gitignore

**Files:**
- Create: `C:/Users/elrug/cv-colegios/.gitignore`
- Create: `C:/Users/elrug/cv-colegios/README.md`

- [ ] **Paso 1: Inicializar el repo y configurar identidad local**

```powershell
cd C:/Users/elrug/cv-colegios
git init
git config user.name "Daniel Eduardo Villalba de Oro"
git config user.email "danedu348@gmail.com"
git branch -M main
```

Expected: mensaje "Initialized empty Git repository".

- [ ] **Paso 2: Crear `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
.pytest_cache/
.coverage
htmlcov/

# Virtual env
venv/
.venv/
env/

# IDE
.vscode/
.idea/
*.swp

# OS
Thumbs.db
.DS_Store

# Secretos del proyecto (NUNCA versionar)
config/.env
config/credentials.json
config/gmail_token.json

# Datos del proyecto
data/colegios.db
data/colegios.db.bak*
data/cv_base.pdf
data/cv_base_polished.pdf
data/plantilla_base.docx
data/salida/
data/logs/

# Archivos temporales
*.tmp
*.log
```

- [ ] **Paso 3: Crear README.md mínimo**

```markdown
# cv-colegios

Herramienta para personalizar y enviar la hoja de vida a colegios privados de Bogotá, Antioquia y Barranquilla.

Diseño completo: `docs/superpowers/specs/2026-05-05-cv-colegios-design.md`

## Estado

En desarrollo. Plan 1 (cimientos) en curso.
```

- [ ] **Paso 4: Hacer el primer commit**

```powershell
git add .gitignore README.md docs/
git commit -m "chore: estructura inicial y diseño del proyecto"
```

Expected: commit creado, `git log` muestra 1 commit.

---

## Tarea 2: Crear la estructura de carpetas y `requirements.txt`

**Files:**
- Create: `C:/Users/elrug/cv-colegios/requirements.txt`
- Create: directorios `data/`, `data/salida/`, `data/logs/`, `modulos/`, `prompts/`, `config/`, `tests/`

- [ ] **Paso 1: Crear directorios**

```powershell
cd C:/Users/elrug/cv-colegios
mkdir -p data/salida, data/logs, modulos, prompts, config, tests
New-Item modulos/__init__.py -ItemType File
New-Item tests/__init__.py -ItemType File
```

- [ ] **Paso 2: Crear `requirements.txt`**

```
anthropic>=0.40.0
python-docx>=1.1.0
python-dotenv>=1.0.0
pdfplumber>=0.11.0
pytest>=8.3.0
pytest-mock>=3.14.0
```

(Las dependencias de scraping y Gmail se agregarán en planes futuros para mantener la instalación liviana.)

- [ ] **Paso 3: Crear entorno virtual e instalar**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Expected: instalación sin errores. Verás `(.venv)` al inicio del prompt.

- [ ] **Paso 4: Verificar pytest funciona**

```powershell
pytest --version
```

Expected: `pytest 8.x.x`.

- [ ] **Paso 5: Commit**

```powershell
git add requirements.txt modulos/ tests/
git commit -m "chore: estructura de carpetas y dependencias base"
```

---

## Tarea 3: Módulo de configuración (carga del .env)

**Files:**
- Create: `config/.env.example`
- Create: `modulos/config.py`
- Test: `tests/test_config.py`

- [ ] **Paso 1: Crear `.env.example` (versionado, sin secretos reales)**

```bash
# Copia este archivo a config/.env y rellena con tus valores reales.
# El archivo .env NUNCA se sube a git (está en .gitignore).

ANTHROPIC_API_KEY=sk-ant-api03-...

# Para planes futuros (todavía no se usan):
GOOGLE_CSE_API_KEY=
GOOGLE_CSE_ENGINE_ID=
CALLMEBOT_API_KEY=
CALLMEBOT_PHONE_NUMBER=
```

- [ ] **Paso 2: Escribir el test que falla**

`tests/test_config.py`:
```python
import os
import pytest
from modulos.config import cargar_config, ConfigError


def test_cargar_config_lee_anthropic_api_key(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-ant-test-123\n")
    config = cargar_config(env_path=env_file)
    assert config["ANTHROPIC_API_KEY"] == "sk-ant-test-123"


def test_cargar_config_falla_si_falta_api_key(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OTRA_VAR=valor\n")
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        cargar_config(env_path=env_file)


def test_cargar_config_falla_si_no_existe_env(tmp_path):
    env_file = tmp_path / "no_existe.env"
    with pytest.raises(ConfigError, match="no encontrado"):
        cargar_config(env_path=env_file)
```

- [ ] **Paso 3: Correr el test y ver que falla**

```powershell
pytest tests/test_config.py -v
```

Expected: FAIL — "ModuleNotFoundError: No module named 'modulos.config'".

- [ ] **Paso 4: Implementar `modulos/config.py`**

```python
from pathlib import Path
from dotenv import dotenv_values


class ConfigError(Exception):
    """Error en la configuración del proyecto."""


REQUERIDAS = ["ANTHROPIC_API_KEY"]


def cargar_config(env_path: Path | str = "config/.env") -> dict[str, str]:
    """Carga la configuración desde un archivo .env y valida que las claves requeridas estén presentes."""
    env_path = Path(env_path)
    if not env_path.exists():
        raise ConfigError(f"Archivo de configuración no encontrado: {env_path}")

    valores = dotenv_values(env_path)
    faltantes = [k for k in REQUERIDAS if not valores.get(k)]
    if faltantes:
        raise ConfigError(f"Variables faltantes en {env_path}: {', '.join(faltantes)}")

    return {k: v for k, v in valores.items() if v is not None}
```

- [ ] **Paso 5: Correr el test y ver que pasa**

```powershell
pytest tests/test_config.py -v
```

Expected: 3 tests PASS.

- [ ] **Paso 6: Commit**

```powershell
git add config/.env.example modulos/config.py tests/test_config.py
git commit -m "feat(config): cargar variables de entorno con validación"
```

---

## Tarea 4: Logger con archivo diario

**Files:**
- Create: `modulos/logger.py`
- Test: `tests/test_logger.py`

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_logger.py`:
```python
from datetime import date
from pathlib import Path
from modulos.logger import obtener_logger


def test_logger_escribe_a_archivo_diario(tmp_path):
    logger = obtener_logger(modulo="prueba", carpeta_logs=tmp_path)
    logger.info("mensaje de prueba")

    archivo_esperado = tmp_path / f"{date.today().isoformat()}.log"
    assert archivo_esperado.exists()
    contenido = archivo_esperado.read_text(encoding="utf-8")
    assert "prueba" in contenido
    assert "mensaje de prueba" in contenido


def test_logger_diferentes_modulos_mismo_archivo(tmp_path):
    log1 = obtener_logger(modulo="m1", carpeta_logs=tmp_path)
    log2 = obtener_logger(modulo="m2", carpeta_logs=tmp_path)
    log1.info("desde m1")
    log2.info("desde m2")

    archivo = tmp_path / f"{date.today().isoformat()}.log"
    contenido = archivo.read_text(encoding="utf-8")
    assert "[m1]" in contenido and "desde m1" in contenido
    assert "[m2]" in contenido and "desde m2" in contenido
```

- [ ] **Paso 2: Correr el test y ver que falla**

```powershell
pytest tests/test_logger.py -v
```

Expected: FAIL — "ModuleNotFoundError".

- [ ] **Paso 3: Implementar `modulos/logger.py`**

```python
import logging
from datetime import date
from pathlib import Path


def obtener_logger(modulo: str, carpeta_logs: Path | str = "data/logs") -> logging.Logger:
    """Devuelve un logger que escribe a un archivo diario y a stdout."""
    carpeta = Path(carpeta_logs)
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"{date.today().isoformat()}.log"

    logger = logging.getLogger(modulo)
    logger.setLevel(logging.INFO)

    if not any(getattr(h, "_cv_archivo", None) == str(archivo) for h in logger.handlers):
        handler = logging.FileHandler(archivo, encoding="utf-8")
        handler._cv_archivo = str(archivo)
        formato = logging.Formatter(f"%(asctime)s [{modulo}] %(levelname)s: %(message)s")
        handler.setFormatter(formato)
        logger.addHandler(handler)

        consola = logging.StreamHandler()
        consola.setFormatter(formato)
        logger.addHandler(consola)

    return logger
```

- [ ] **Paso 4: Correr el test y ver que pasa**

```powershell
pytest tests/test_logger.py -v
```

Expected: 2 tests PASS.

- [ ] **Paso 5: Commit**

```powershell
git add modulos/logger.py tests/test_logger.py
git commit -m "feat(logger): logging a archivo diario por módulo"
```

---

## Tarea 5: Cliente de Claude (con prompt caching)

**Files:**
- Create: `modulos/cliente_claude.py`
- Test: `tests/test_cliente_claude.py`

- [ ] **Paso 1: Escribir el test que falla (con mock)**

`tests/test_cliente_claude.py`:
```python
from unittest.mock import MagicMock, patch
from modulos.cliente_claude import ClienteClaude


def test_cliente_envia_prompt_y_devuelve_texto():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="respuesta de prueba")]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50

    with patch("modulos.cliente_claude.Anthropic") as mock_anthropic:
        instancia = mock_anthropic.return_value
        instancia.messages.create.return_value = mock_response

        cliente = ClienteClaude(api_key="sk-ant-test")
        texto, costo = cliente.preguntar(
            sistema="Eres un asistente.",
            usuario="Hola",
        )

        assert texto == "respuesta de prueba"
        assert costo > 0


def test_cliente_falla_sin_api_key():
    import pytest
    with pytest.raises(ValueError, match="api_key"):
        ClienteClaude(api_key="")
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_cliente_claude.py -v
```

Expected: FAIL — "ModuleNotFoundError".

- [ ] **Paso 3: Implementar `modulos/cliente_claude.py`**

```python
from anthropic import Anthropic


MODELO = "claude-sonnet-4-6"

# Tarifas USD por millón de tokens (Sonnet 4.6 al 2026-05; ajustar si cambia)
PRECIO_INPUT = 3.0
PRECIO_OUTPUT = 15.0


class ClienteClaude:
    """Wrapper sobre el SDK de Anthropic con cálculo de costo y prompt caching."""

    def __init__(self, api_key: str, modelo: str = MODELO):
        if not api_key:
            raise ValueError("api_key es requerida")
        self.cliente = Anthropic(api_key=api_key)
        self.modelo = modelo

    def preguntar(
        self,
        sistema: str,
        usuario: str,
        max_tokens: int = 4096,
        cachear_sistema: bool = False,
    ) -> tuple[str, float]:
        """Envía un prompt y devuelve (texto_respuesta, costo_estimado_usd)."""
        sistema_param = sistema
        if cachear_sistema:
            sistema_param = [{
                "type": "text",
                "text": sistema,
                "cache_control": {"type": "ephemeral"},
            }]

        respuesta = self.cliente.messages.create(
            model=self.modelo,
            max_tokens=max_tokens,
            system=sistema_param,
            messages=[{"role": "user", "content": usuario}],
        )

        texto = "".join(b.text for b in respuesta.content if hasattr(b, "text"))
        costo = (
            respuesta.usage.input_tokens * PRECIO_INPUT
            + respuesta.usage.output_tokens * PRECIO_OUTPUT
        ) / 1_000_000
        return texto, costo
```

- [ ] **Paso 4: Correr y ver pasar**

```powershell
pytest tests/test_cliente_claude.py -v
```

Expected: 2 tests PASS.

- [ ] **Paso 5: Commit**

```powershell
git add modulos/cliente_claude.py tests/test_cliente_claude.py
git commit -m "feat(claude): wrapper con cálculo de costo y prompt caching"
```

---

## Tarea 6: Esquema SQL de la BD

**Files:**
- Create: `modulos/schema.sql`

- [ ] **Paso 1: Escribir el archivo de esquema**

`modulos/schema.sql`:
```sql
-- Tabla principal: un colegio por fila
CREATE TABLE IF NOT EXISTS colegios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    nombre_normalizado TEXT NOT NULL,
    ciudad TEXT NOT NULL,
    departamento TEXT NOT NULL,
    nit TEXT,
    web TEXT,
    correo TEXT,
    correo_destinatario TEXT,
    fuente TEXT NOT NULL,
    perfil_pedagogico TEXT,        -- JSON
    palabras_clave TEXT,           -- JSON list
    estado TEXT NOT NULL DEFAULT 'descubierto',
    intentos_enriquecer INTEGER NOT NULL DEFAULT 0,
    intentos_generar INTEGER NOT NULL DEFAULT 0,
    fecha_descubierto DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_enriquecido DATETIME,
    fecha_envio DATETIME,
    fecha_respuesta DATETIME,
    gmail_draft_id TEXT,
    gmail_thread_id TEXT,
    notas TEXT,
    CHECK (estado IN (
        'descubierto', 'enriquecido', 'sin_correo', 'borrador_creado',
        'enviado', 'respondió', 'rebotó', 'seguimiento_pendiente',
        'sin_respuesta', 'descartado', 'error', 'revisar_manualmente'
    ))
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_colegios_dedup
    ON colegios(nombre_normalizado, ciudad);

CREATE UNIQUE INDEX IF NOT EXISTS ix_colegios_nit
    ON colegios(nit) WHERE nit IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_colegios_estado ON colegios(estado);
CREATE INDEX IF NOT EXISTS ix_colegios_thread ON colegios(gmail_thread_id);

-- Tabla de borradores generados (un colegio puede tener varios: inicial + seguimiento)
CREATE TABLE IF NOT EXISTS borradores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('inicial', 'seguimiento')),
    asunto TEXT NOT NULL,
    cuerpo_carta TEXT NOT NULL,
    ruta_pdf_hv TEXT,
    estado TEXT NOT NULL DEFAULT 'listo_para_subir'
        CHECK (estado IN ('listo_para_subir', 'subido', 'fallo')),
    gmail_draft_id TEXT,
    fecha_creado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_subido DATETIME,
    error_mensaje TEXT
);

CREATE INDEX IF NOT EXISTS ix_borradores_estado ON borradores(estado);
CREATE INDEX IF NOT EXISTS ix_borradores_colegio ON borradores(colegio_id);

-- Tabla de auditoría de ejecuciones
CREATE TABLE IF NOT EXISTS registro_ejecuciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulo TEXT NOT NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duracion_segundos REAL,
    estado TEXT NOT NULL CHECK (estado IN ('ok', 'error')),
    colegios_procesados INTEGER NOT NULL DEFAULT 0,
    mensaje TEXT,
    costo_api_usd REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_registro_modulo_fecha
    ON registro_ejecuciones(modulo, fecha);
```

- [ ] **Paso 2: Commit**

```powershell
git add modulos/schema.sql
git commit -m "feat(db): esquema SQL con 3 tablas y constraints"
```

---

## Tarea 7: Conexión a la BD e inicialización

**Files:**
- Create: `modulos/db.py`
- Create: `init_db.py`
- Test: `tests/test_db_init.py`

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_db_init.py`:
```python
import sqlite3
from pathlib import Path
from modulos.db import inicializar_db, conectar


def test_inicializar_crea_tablas(tmp_path):
    ruta = tmp_path / "test.db"
    inicializar_db(ruta)
    conn = conectar(ruta)
    tablas = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "colegios" in tablas
    assert "borradores" in tablas
    assert "registro_ejecuciones" in tablas


def test_inicializar_es_idempotente(tmp_path):
    ruta = tmp_path / "test.db"
    inicializar_db(ruta)
    inicializar_db(ruta)  # No debe fallar
    conn = conectar(ruta)
    count = conn.execute("SELECT COUNT(*) FROM colegios").fetchone()[0]
    conn.close()
    assert count == 0


def test_constraint_estado_invalido(tmp_path):
    ruta = tmp_path / "test.db"
    inicializar_db(ruta)
    conn = conectar(ruta)
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO colegios "
            "(nombre, nombre_normalizado, ciudad, departamento, fuente, estado) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("X", "x", "Bogotá", "Bogotá D.C.", "MEN", "estado_inventado"),
        )
    conn.close()
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_db_init.py -v
```

Expected: FAIL.

- [ ] **Paso 3: Implementar `modulos/db.py`**

```python
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def conectar(ruta: Path | str) -> sqlite3.Connection:
    """Devuelve una conexión a la BD con foreign keys activadas."""
    conn = sqlite3.connect(str(ruta))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db(ruta: Path | str) -> None:
    """Crea la BD si no existe y aplica el schema (idempotente)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = conectar(ruta)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Paso 4: Implementar `init_db.py` (CLI)**

```python
"""Comando único: crea data/colegios.db si no existe."""
from pathlib import Path
from modulos.db import inicializar_db

RUTA_BD = Path("data/colegios.db")


def main():
    inicializar_db(RUTA_BD)
    print(f"Base de datos lista en {RUTA_BD.resolve()}")


if __name__ == "__main__":
    main()
```

- [ ] **Paso 5: Correr y ver pasar**

```powershell
pytest tests/test_db_init.py -v
python init_db.py
```

Expected: 3 tests PASS. CLI imprime "Base de datos lista en C:\Users\elrug\cv-colegios\data\colegios.db".

- [ ] **Paso 6: Commit**

```powershell
git add modulos/db.py init_db.py tests/test_db_init.py
git commit -m "feat(db): conexión, inicialización y constraint de estados"
```

---

## Tarea 8: Inserción de colegios con deduplicación

**Files:**
- Modify: `modulos/db.py`
- Create: `modulos/normalizar.py`
- Test: `tests/test_db_insert.py`
- Test: `tests/test_normalizar.py`

- [ ] **Paso 1: Test de normalización (red)**

`tests/test_normalizar.py`:
```python
from modulos.normalizar import normalizar_nombre


def test_normaliza_minusculas_y_acentos():
    assert normalizar_nombre("Colegio San José") == "san jose"


def test_remueve_sufijos_legales():
    assert normalizar_nombre("Colegio San Carlos S.A.S.") == "san carlos"
    assert normalizar_nombre("Institución Educativa Santa María Ltda.") == "santa maria"


def test_colapsa_espacios():
    assert normalizar_nombre("  Colegio   Bilingüe   ABC  ") == "bilingue abc"


def test_remueve_palabras_genericas():
    assert normalizar_nombre("Corporación Colegio Gimnasio Moderno") == "moderno"
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_normalizar.py -v
```

- [ ] **Paso 3: Implementar `modulos/normalizar.py`**

```python
import re
import unicodedata

SUFIJOS = {"sas", "sa", "ltda", "spa"}
PALABRAS_GENERICAS = {"colegio", "institucion", "corporacion", "gimnasio", "liceo", "escuela", "educativa", "instituto"}


def normalizar_nombre(nombre: str) -> str:
    """Normaliza un nombre de colegio para deduplicación."""
    sin_acentos = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii")
    sin_puntos = sin_acentos.replace(".", "").lower()
    palabras = re.findall(r"\w+", sin_puntos)
    filtradas = [p for p in palabras if p not in PALABRAS_GENERICAS and p not in SUFIJOS]
    return " ".join(filtradas)
```

- [ ] **Paso 4: Correr y ver pasar**

```powershell
pytest tests/test_normalizar.py -v
```

Expected: 4 PASS.

- [ ] **Paso 5: Test de inserción con dedup (red)**

`tests/test_db_insert.py`:
```python
import pytest
from modulos.db import inicializar_db, insertar_colegio, contar_colegios


def test_insertar_colegio_nuevo(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    insertar_colegio(ruta, nombre="Colegio San Tarsicio", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="MEN", nit="800123456-7")
    assert contar_colegios(ruta) == 1


def test_insertar_duplicado_por_nit_no_duplica(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    insertar_colegio(ruta, nombre="Colegio X", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="MEN", nit="800-1")
    insertar_colegio(ruta, nombre="Otro Nombre del mismo colegio", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="UNCOLI", nit="800-1")
    assert contar_colegios(ruta) == 1


def test_insertar_duplicado_por_nombre_normalizado(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    insertar_colegio(ruta, nombre="Colegio San José", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="MEN")
    insertar_colegio(ruta, nombre="COLEGIO SAN JOSE S.A.S.", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="UNCOLI")
    assert contar_colegios(ruta) == 1


def test_mismo_nombre_distinta_ciudad_son_distintos(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    insertar_colegio(ruta, nombre="Colegio San José", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="MEN")
    insertar_colegio(ruta, nombre="Colegio San José", ciudad="Medellín",
                     departamento="Antioquia", fuente="MEN")
    assert contar_colegios(ruta) == 2


def test_dedup_acumula_fuente(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    insertar_colegio(ruta, nombre="Colegio X", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="MEN")
    insertar_colegio(ruta, nombre="Colegio X", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="UNCOLI")
    from modulos.db import conectar
    conn = conectar(ruta)
    fuente = conn.execute("SELECT fuente FROM colegios").fetchone()["fuente"]
    conn.close()
    assert "MEN" in fuente and "UNCOLI" in fuente
```

- [ ] **Paso 6: Correr y ver fallar**

```powershell
pytest tests/test_db_insert.py -v
```

- [ ] **Paso 7: Agregar funciones a `modulos/db.py`**

Agregar al final de `modulos/db.py`:

```python
from modulos.normalizar import normalizar_nombre


def insertar_colegio(
    ruta_bd,
    *,
    nombre: str,
    ciudad: str,
    departamento: str,
    fuente: str,
    nit: str | None = None,
    web: str | None = None,
    correo: str | None = None,
) -> int:
    """Inserta un colegio. Si ya existe (por NIT o nombre+ciudad), acumula fuente. Devuelve id."""
    nombre_norm = normalizar_nombre(nombre)
    conn = conectar(ruta_bd)
    try:
        # Buscar duplicado
        row = None
        if nit:
            row = conn.execute("SELECT id, fuente FROM colegios WHERE nit = ?", (nit,)).fetchone()
        if not row:
            row = conn.execute(
                "SELECT id, fuente FROM colegios WHERE nombre_normalizado = ? AND ciudad = ?",
                (nombre_norm, ciudad),
            ).fetchone()

        if row:
            fuentes = set(row["fuente"].split(","))
            fuentes.add(fuente)
            nueva = ",".join(sorted(fuentes))
            conn.execute("UPDATE colegios SET fuente = ? WHERE id = ?", (nueva, row["id"]))
            # Completar campos vacíos sin sobrescribir
            for campo, valor in [("nit", nit), ("web", web), ("correo", correo)]:
                if valor:
                    conn.execute(
                        f"UPDATE colegios SET {campo} = COALESCE({campo}, ?) WHERE id = ?",
                        (valor, row["id"]),
                    )
            conn.commit()
            return row["id"]

        cur = conn.execute(
            """INSERT INTO colegios (nombre, nombre_normalizado, ciudad, departamento,
                                      nit, web, correo, fuente)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (nombre, nombre_norm, ciudad, departamento, nit, web, correo, fuente),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def contar_colegios(ruta_bd) -> int:
    conn = conectar(ruta_bd)
    try:
        return conn.execute("SELECT COUNT(*) FROM colegios").fetchone()[0]
    finally:
        conn.close()
```

- [ ] **Paso 8: Correr y ver pasar**

```powershell
pytest tests/test_db_insert.py tests/test_normalizar.py -v
```

Expected: 9 tests PASS (5 + 4).

- [ ] **Paso 9: Commit**

```powershell
git add modulos/normalizar.py modulos/db.py tests/test_normalizar.py tests/test_db_insert.py
git commit -m "feat(db): inserción de colegios con deduplicación por NIT y nombre"
```

---

## Tarea 9: Transiciones de estado validadas

**Files:**
- Modify: `modulos/db.py`
- Test: `tests/test_db_estados.py`

- [ ] **Paso 1: Test de transiciones (red)**

`tests/test_db_estados.py`:
```python
import pytest
from modulos.db import (
    inicializar_db, insertar_colegio, cambiar_estado,
    obtener_estado, EstadoInvalidoError,
)


def _crear(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    cid = insertar_colegio(ruta, nombre="X", ciudad="Bogotá",
                            departamento="Bogotá D.C.", fuente="MEN")
    return ruta, cid


def test_transicion_valida(tmp_path):
    ruta, cid = _crear(tmp_path)
    cambiar_estado(ruta, cid, "enriquecido")
    assert obtener_estado(ruta, cid) == "enriquecido"


def test_transicion_invalida_falla(tmp_path):
    ruta, cid = _crear(tmp_path)
    cambiar_estado(ruta, cid, "enriquecido")
    with pytest.raises(EstadoInvalidoError, match="no se puede pasar"):
        cambiar_estado(ruta, cid, "descubierto")


def test_descartado_desde_cualquier_estado(tmp_path):
    ruta, cid = _crear(tmp_path)
    cambiar_estado(ruta, cid, "enriquecido")
    cambiar_estado(ruta, cid, "borrador_creado")
    cambiar_estado(ruta, cid, "descartado")
    assert obtener_estado(ruta, cid) == "descartado"


def test_estado_inexistente_falla(tmp_path):
    ruta, cid = _crear(tmp_path)
    with pytest.raises(EstadoInvalidoError, match="estado desconocido"):
        cambiar_estado(ruta, cid, "estado_que_no_existe")
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_db_estados.py -v
```

- [ ] **Paso 3: Agregar a `modulos/db.py`**

```python
class EstadoInvalidoError(Exception):
    pass


TRANSICIONES_VALIDAS = {
    "descubierto": {"enriquecido", "sin_correo", "error", "descartado", "revisar_manualmente"},
    "enriquecido": {"borrador_creado", "descartado", "revisar_manualmente"},
    "sin_correo": {"enriquecido", "descartado"},  # si se llena correo a mano
    "borrador_creado": {"enviado", "rebotó", "descartado"},
    "enviado": {"respondió", "seguimiento_pendiente", "rebotó", "descartado"},
    "seguimiento_pendiente": {"respondió", "sin_respuesta", "descartado"},
    "respondió": {"descartado"},
    "rebotó": {"descartado"},
    "sin_respuesta": {"descartado"},
    "descartado": set(),
    "error": {"descubierto", "descartado"},  # reintento manual
    "revisar_manualmente": {"enriquecido", "descartado"},
}

ESTADOS_VALIDOS = set(TRANSICIONES_VALIDAS.keys())


def obtener_estado(ruta_bd, colegio_id: int) -> str:
    conn = conectar(ruta_bd)
    try:
        row = conn.execute("SELECT estado FROM colegios WHERE id = ?", (colegio_id,)).fetchone()
        if not row:
            raise EstadoInvalidoError(f"colegio id={colegio_id} no existe")
        return row["estado"]
    finally:
        conn.close()


def cambiar_estado(ruta_bd, colegio_id: int, nuevo_estado: str) -> None:
    if nuevo_estado not in ESTADOS_VALIDOS:
        raise EstadoInvalidoError(f"estado desconocido: {nuevo_estado}")
    actual = obtener_estado(ruta_bd, colegio_id)
    if nuevo_estado not in TRANSICIONES_VALIDAS[actual]:
        raise EstadoInvalidoError(
            f"no se puede pasar de {actual} a {nuevo_estado}"
        )
    conn = conectar(ruta_bd)
    try:
        conn.execute("UPDATE colegios SET estado = ? WHERE id = ?", (nuevo_estado, colegio_id))
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Paso 4: Correr y ver pasar**

```powershell
pytest tests/test_db_estados.py -v
```

Expected: 4 PASS.

- [ ] **Paso 5: Commit**

```powershell
git add modulos/db.py tests/test_db_estados.py
git commit -m "feat(db): máquina de estados con transiciones validadas"
```

---

## Tarea 10: Backups rotativos de la BD

**Files:**
- Create: `modulos/backup.py`
- Test: `tests/test_backup.py`

- [ ] **Paso 1: Test (red)**

`tests/test_backup.py`:
```python
from pathlib import Path
from modulos.backup import respaldar_bd, RETENCION_DIAS


def test_crea_archivo_bak(tmp_path):
    bd = tmp_path / "x.db"
    bd.write_bytes(b"contenido original")
    respaldar_bd(bd)
    assert (tmp_path / "x.db.bak.1").exists()
    assert (tmp_path / "x.db.bak.1").read_bytes() == b"contenido original"


def test_rota_backups_y_limita_retencion(tmp_path):
    bd = tmp_path / "x.db"
    for i in range(RETENCION_DIAS + 3):
        bd.write_bytes(f"v{i}".encode())
        respaldar_bd(bd)
    backups = sorted(tmp_path.glob("x.db.bak.*"))
    assert len(backups) == RETENCION_DIAS
    # El más reciente (.bak.1) tiene el contenido más nuevo
    assert (tmp_path / "x.db.bak.1").read_bytes() == f"v{RETENCION_DIAS + 2}".encode()


def test_no_falla_si_no_existe_bd(tmp_path):
    bd = tmp_path / "no_existe.db"
    respaldar_bd(bd)  # no debe lanzar excepción
    assert not (tmp_path / "no_existe.db.bak.1").exists()
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_backup.py -v
```

- [ ] **Paso 3: Implementar `modulos/backup.py`**

```python
import shutil
from pathlib import Path

RETENCION_DIAS = 7


def respaldar_bd(ruta_bd: Path | str) -> None:
    """Crea bak.1 (más reciente), rotando los anteriores. Borra los que excedan retención."""
    ruta_bd = Path(ruta_bd)
    if not ruta_bd.exists():
        return

    # Borrar el más viejo si excede retención
    viejo = ruta_bd.with_suffix(ruta_bd.suffix + f".bak.{RETENCION_DIAS}")
    if viejo.exists():
        viejo.unlink()

    # Rotar: bak.6 -> bak.7, bak.5 -> bak.6, ..., bak.1 -> bak.2
    for i in range(RETENCION_DIAS - 1, 0, -1):
        actual = ruta_bd.with_suffix(ruta_bd.suffix + f".bak.{i}")
        siguiente = ruta_bd.with_suffix(ruta_bd.suffix + f".bak.{i + 1}")
        if actual.exists():
            actual.rename(siguiente)

    # Crear bak.1 a partir del archivo actual
    bak1 = ruta_bd.with_suffix(ruta_bd.suffix + ".bak.1")
    shutil.copy2(ruta_bd, bak1)
```

- [ ] **Paso 4: Correr y ver pasar**

```powershell
pytest tests/test_backup.py -v
```

Expected: 3 PASS.

- [ ] **Paso 5: Commit**

```powershell
git add modulos/backup.py tests/test_backup.py
git commit -m "feat(backup): respaldo rotativo con retención de 7 días"
```

---

## Tarea 11: Validador anti-alucinación — extracción de tokens

**Files:**
- Create: `modulos/validador.py`
- Test: `tests/test_validador_extraer.py`

- [ ] **Paso 1: Test (red)**

`tests/test_validador_extraer.py`:
```python
from modulos.validador import extraer_hechos


def test_extrae_anios():
    assert "2024" in extraer_hechos("Graduado en 2024 de la universidad")


def test_extrae_isbn():
    assert "978-99993-2-001-6" in extraer_hechos("ISBN: 978-99993-2-001-6 publicado")


def test_extrae_doi():
    assert "10.15648/redfids.16.2025.4684" in extraer_hechos(
        "DOI: https://doi.org/10.15648/redfids.16.2025.4684 disponible"
    )


def test_extrae_nombres_propios_multipalabra():
    hechos = extraer_hechos("Trabajé en la Universidad de Córdoba con el profesor Juan Andres Contreras Baltazar.")
    assert "Universidad de Córdoba" in hechos
    assert "Juan Andres Contreras Baltazar" in hechos


def test_no_extrae_palabras_comunes():
    hechos = extraer_hechos("La Educación Física es importante.")
    # 'La' al inicio de oración no debe contar como nombre propio aislado
    assert "La" not in hechos


def test_extrae_porcentajes_y_horas():
    hechos = extraer_hechos("Curso de 60 horas con 95% de asistencia.")
    assert "60" in hechos
    assert "95" in hechos
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_validador_extraer.py -v
```

- [ ] **Paso 3: Implementar `modulos/validador.py`**

```python
import re

# Regex para identificar tokens "verificables"
RE_ANIO = re.compile(r"\b(19|20)\d{2}\b")
RE_NUMERO = re.compile(r"\b\d{1,4}\b")
RE_ISBN = re.compile(r"\b(?:97[89][- ]?)?\d{1,5}[- ]?\d{1,7}[- ]?\d{1,7}[- ]?[\dX]\b")
RE_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
RE_PROPIO = re.compile(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de\s+|del\s+|la\s+|las\s+|los\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*\b")


def extraer_hechos(texto: str) -> set[str]:
    """Devuelve el conjunto de tokens 'verificables' (años, números, nombres propios, ISBNs, DOIs)."""
    hechos = set()
    hechos.update(RE_ANIO.findall(texto))
    hechos.update(RE_ISBN.findall(texto))
    hechos.update(RE_DOI.findall(texto))
    hechos.update(RE_NUMERO.findall(texto))
    # Convertir años de tupla (cuando RE_ANIO captura grupo) a string completo
    hechos.update(m.group(0) for m in RE_ANIO.finditer(texto))
    # Nombres propios de 2+ palabras, descartando palabras al inicio de oración
    for match in RE_PROPIO.finditer(texto):
        candidato = match.group(0)
        if " " in candidato:
            hechos.add(candidato)
        else:
            # Una sola palabra: solo si NO está al inicio de oración
            inicio = match.start()
            if inicio > 0 and texto[inicio - 1] not in ".!?":
                hechos.add(candidato)
    return hechos
```

- [ ] **Paso 4: Correr y ver pasar**

```powershell
pytest tests/test_validador_extraer.py -v
```

Expected: 6 PASS.

- [ ] **Paso 5: Commit**

```powershell
git add modulos/validador.py tests/test_validador_extraer.py
git commit -m "feat(validador): extracción de tokens verificables"
```

---

## Tarea 12: Validador anti-alucinación — comparación

**Files:**
- Modify: `modulos/validador.py`
- Test: `tests/test_validador_comparar.py`

- [ ] **Paso 1: Test (red)**

`tests/test_validador_comparar.py`:
```python
from modulos.validador import detectar_alucinaciones


def test_sin_hechos_nuevos_no_aluciona():
    cv = "Daniel trabajó en Universidad de Córdoba en 2024."
    salida = "Daniel trabajó en la Universidad de Córdoba durante 2024."
    assert detectar_alucinaciones(cv_original=cv, texto_generado=salida) == set()


def test_anio_inventado_es_detectado():
    cv = "Daniel se graduó en 2024."
    salida = "Daniel se graduó en 2025."  # 2025 no está en el CV
    nuevos = detectar_alucinaciones(cv_original=cv, texto_generado=salida)
    assert "2025" in nuevos


def test_universidad_inventada_es_detectada():
    cv = "Daniel trabajó en Universidad de Córdoba."
    salida = "Daniel trabajó en Harvard University."
    nuevos = detectar_alucinaciones(cv_original=cv, texto_generado=salida)
    assert any("Harvard" in n for n in nuevos)


def test_nombre_propio_del_destinatario_no_cuenta():
    """Si el colegio se llama 'San Tarsicio', mencionarlo no es alucinación."""
    cv = "Daniel es docente."
    salida = "Estimado rector del Colegio San Tarsicio, Daniel es docente."
    nuevos = detectar_alucinaciones(
        cv_original=cv, texto_generado=salida,
        nombres_permitidos={"Colegio San Tarsicio"},
    )
    assert "Colegio San Tarsicio" not in nuevos
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_validador_comparar.py -v
```

- [ ] **Paso 3: Agregar a `modulos/validador.py`**

```python
def detectar_alucinaciones(
    cv_original: str,
    texto_generado: str,
    nombres_permitidos: set[str] | None = None,
) -> set[str]:
    """Devuelve los hechos del texto_generado que NO están en cv_original ni en nombres_permitidos."""
    hechos_cv = extraer_hechos(cv_original)
    hechos_generado = extraer_hechos(texto_generado)
    permitidos = nombres_permitidos or set()
    return hechos_generado - hechos_cv - permitidos
```

- [ ] **Paso 4: Correr y ver pasar**

```powershell
pytest tests/test_validador_comparar.py -v
```

Expected: 4 PASS.

- [ ] **Paso 5: Commit**

```powershell
git add modulos/validador.py tests/test_validador_comparar.py
git commit -m "feat(validador): detección de hechos alucinados con whitelist"
```

---

## Tarea 13: Lectura de PDF (pdfplumber)

**Files:**
- Create: `modulos/pdf_lector.py`
- Test: `tests/test_pdf_lector.py`
- Test fixture: `tests/fixtures/cv_minimo.pdf` (lo construye el test desde texto)

- [ ] **Paso 1: Test (red)**

`tests/test_pdf_lector.py`:
```python
from pathlib import Path
import pytest
from modulos.pdf_lector import leer_pdf


@pytest.fixture
def pdf_de_prueba(tmp_path):
    """Genera un PDF de prueba con docx para no depender de un archivo binario en el repo."""
    from docx import Document
    import subprocess
    docx_path = tmp_path / "test.docx"
    pdf_path = tmp_path / "test.pdf"
    doc = Document()
    doc.add_paragraph("Daniel Eduardo Villalba")
    doc.add_paragraph("Licenciado en educación física, 2024")
    doc.add_paragraph("ISBN: 978-99993-2-001-6")
    doc.save(docx_path)
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", str(docx_path), "--outdir", str(tmp_path)],
        check=True, capture_output=True,
    )
    return pdf_path


def test_leer_pdf_extrae_texto(pdf_de_prueba):
    texto = leer_pdf(pdf_de_prueba)
    assert "Daniel Eduardo Villalba" in texto
    assert "2024" in texto
    assert "978-99993-2-001-6" in texto
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_pdf_lector.py -v
```

- [ ] **Paso 3: Implementar `modulos/pdf_lector.py`**

```python
from pathlib import Path
import pdfplumber


def leer_pdf(ruta: Path | str) -> str:
    """Extrae todo el texto de un PDF, página por página."""
    ruta = Path(ruta)
    paginas = []
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                paginas.append(texto)
    return "\n\n".join(paginas)
```

- [ ] **Paso 4: Correr y ver pasar**

```powershell
pytest tests/test_pdf_lector.py -v
```

Expected: 1 PASS (puede tardar 5-10s por la conversión LibreOffice).

- [ ] **Paso 5: Commit**

```powershell
git add modulos/pdf_lector.py tests/test_pdf_lector.py
git commit -m "feat(pdf): extracción de texto con pdfplumber"
```

---

## Tarea 14: Conversor DOCX → PDF (LibreOffice)

**Files:**
- Create: `modulos/pdf_conversor.py`
- Test: `tests/test_pdf_conversor.py`

- [ ] **Paso 1: Test (red)**

`tests/test_pdf_conversor.py`:
```python
from pathlib import Path
from docx import Document
from modulos.pdf_conversor import convertir_docx_a_pdf


def test_convierte_docx_a_pdf(tmp_path):
    docx_path = tmp_path / "entrada.docx"
    pdf_path = tmp_path / "entrada.pdf"
    doc = Document()
    doc.add_paragraph("Texto de prueba para conversion.")
    doc.save(docx_path)

    convertir_docx_a_pdf(docx_path, pdf_path)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 100  # PDF no vacío
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_pdf_conversor.py -v
```

- [ ] **Paso 3: Implementar `modulos/pdf_conversor.py`**

```python
import shutil
import subprocess
from pathlib import Path


class ConversionError(Exception):
    pass


def _ruta_libreoffice() -> str:
    """Encuentra el ejecutable de LibreOffice. Prefiere 'soffice' en PATH; cae a Windows estándar."""
    if shutil.which("soffice"):
        return "soffice"
    candidatos = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for c in candidatos:
        if Path(c).exists():
            return c
    raise ConversionError("LibreOffice no encontrado. Instálalo desde libreoffice.org")


def convertir_docx_a_pdf(docx_path: Path | str, pdf_path: Path | str) -> None:
    """Convierte un DOCX a PDF usando LibreOffice headless."""
    docx_path = Path(docx_path)
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    soffice = _ruta_libreoffice()
    resultado = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", str(docx_path),
         "--outdir", str(pdf_path.parent)],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        raise ConversionError(f"LibreOffice falló: {resultado.stderr}")

    # LibreOffice nombra el output con el mismo nombre del docx, extensión pdf
    salida_lo = pdf_path.parent / (docx_path.stem + ".pdf")
    if salida_lo != pdf_path:
        salida_lo.rename(pdf_path)
```

- [ ] **Paso 4: Correr y ver pasar**

```powershell
pytest tests/test_pdf_conversor.py -v
```

Expected: 1 PASS.

- [ ] **Paso 5: Commit**

```powershell
git add modulos/pdf_conversor.py tests/test_pdf_conversor.py
git commit -m "feat(pdf): conversión DOCX→PDF con LibreOffice headless"
```

---

## Tarea 15: Motor de plantillas DOCX

**Files:**
- Create: `modulos/plantilla.py`
- Test: `tests/test_plantilla.py`

- [ ] **Paso 1: Test (red)**

`tests/test_plantilla.py`:
```python
from pathlib import Path
from docx import Document
from modulos.plantilla import rellenar_plantilla


def _crear_plantilla(tmp_path) -> Path:
    doc = Document()
    doc.add_heading("{{NOMBRE}}", level=1)
    doc.add_paragraph("{{PERFIL}}")
    doc.add_heading("Experiencia", level=2)
    doc.add_paragraph("{{EXP_1_TITULO}}")
    p = tmp_path / "plantilla.docx"
    doc.save(p)
    return p


def test_rellenar_plantilla_reemplaza_placeholders(tmp_path):
    plantilla = _crear_plantilla(tmp_path)
    salida = tmp_path / "salida.docx"

    rellenar_plantilla(
        plantilla,
        salida,
        valores={
            "NOMBRE": "Daniel Villalba",
            "PERFIL": "Docente con experiencia en TIC.",
            "EXP_1_TITULO": "Colegio Inocencio Chincá",
        },
    )

    doc = Document(salida)
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "Daniel Villalba" in texto
    assert "Docente con experiencia en TIC." in texto
    assert "Colegio Inocencio Chincá" in texto
    assert "{{NOMBRE}}" not in texto


def test_rellenar_falla_si_falta_valor(tmp_path):
    plantilla = _crear_plantilla(tmp_path)
    salida = tmp_path / "salida.docx"
    import pytest
    with pytest.raises(ValueError, match="placeholder"):
        rellenar_plantilla(plantilla, salida, valores={"NOMBRE": "X"})
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_plantilla.py -v
```

- [ ] **Paso 3: Implementar `modulos/plantilla.py`**

```python
import re
from pathlib import Path
from docx import Document

RE_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def rellenar_plantilla(
    plantilla_path: Path | str,
    salida_path: Path | str,
    valores: dict[str, str],
) -> None:
    """Carga una plantilla DOCX, reemplaza {{NOMBRE}}-style placeholders, guarda en salida."""
    doc = Document(str(plantilla_path))
    placeholders_encontrados = set()

    def reemplazar_en_runs(parrafo):
        # python-docx parte el texto en "runs"; reemplazamos sobre el texto del párrafo completo
        texto_completo = parrafo.text
        for match in RE_PLACEHOLDER.finditer(texto_completo):
            placeholders_encontrados.add(match.group(1))
        nuevo_texto = RE_PLACEHOLDER.sub(
            lambda m: valores.get(m.group(1), m.group(0)),
            texto_completo,
        )
        if nuevo_texto != texto_completo:
            # Limpiar runs y poner el texto en el primer run
            for run in parrafo.runs:
                run.text = ""
            if parrafo.runs:
                parrafo.runs[0].text = nuevo_texto
            else:
                parrafo.add_run(nuevo_texto)

    for parrafo in doc.paragraphs:
        reemplazar_en_runs(parrafo)
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                for parrafo in celda.paragraphs:
                    reemplazar_en_runs(parrafo)

    faltantes = placeholders_encontrados - set(valores.keys())
    if faltantes:
        raise ValueError(f"placeholder(s) sin valor: {sorted(faltantes)}")

    Path(salida_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(salida_path))
```

- [ ] **Paso 4: Correr y ver pasar**

```powershell
pytest tests/test_plantilla.py -v
```

Expected: 2 PASS.

- [ ] **Paso 5: Commit**

```powershell
git add modulos/plantilla.py tests/test_plantilla.py
git commit -m "feat(plantilla): motor de reemplazo de placeholders en DOCX"
```

---

## Tarea 16: Prompt para pulir el CV

**Files:**
- Create: `prompts/pulir_cv.txt`

- [ ] **Paso 1: Crear el prompt**

`prompts/pulir_cv.txt`:
```
Eres un editor profesional de hojas de vida en español colombiano.

Recibirás el texto plano de una hoja de vida. Tu tarea es producir DOS salidas:

1. UNA VERSIÓN PULIDA: el mismo contenido pero con:
   - Errores ortográficos corregidos (ej: "INTITUCIÓN" → "INSTITUCIÓN", "phyton" → "Python", "TRANNING" → "TRAINING").
   - Acentos faltantes restituidos.
   - Fechas unificadas a formato "DD/MM/AAAA".
   - Bloques mal formateados (como el de idiomas) reorganizados con saltos de línea claros.
   - Sin agregar, omitir ni inventar información.

2. UNA VERSIÓN CON PLACEHOLDERS: la misma versión pulida pero con los siguientes campos reemplazados por placeholders {{NOMBRE_VARIABLE}}:
   - {{PERFIL}}: el bloque de "Perfil" completo (los 2 párrafos del inicio).
   - {{EXP_N_TITULO}}, {{EXP_N_BULLETS}}: para cada experiencia, su título y sus bullets (numerar 1, 2, 3...).

Devuelve EXACTAMENTE este formato JSON, sin nada antes ni después:

```json
{
  "version_pulida": "<texto plano completo, con saltos de línea \\n>",
  "version_con_placeholders": "<texto con {{PERFIL}}, {{EXP_1_TITULO}}, etc.>",
  "cambios_realizados": [
    "INTITUCIÓN → INSTITUCIÓN (4 ocurrencias)",
    "..."
  ],
  "advertencias": [
    "<cosas que dudaste o consideraste; vacío si todo claro>"
  ]
}
```

NO inventes datos. Si dudas de algo, déjalo igual y agrégalo a "advertencias".
```

- [ ] **Paso 2: Commit**

```powershell
git add prompts/pulir_cv.txt
git commit -m "feat(prompts): prompt para pulir CV con doble salida"
```

---

## Tarea 17: Comando `reconstruir_plantilla.py` — esqueleto y lectura del PDF

**Files:**
- Create: `reconstruir_plantilla.py`
- Test: `tests/test_reconstruir_plantilla.py`

- [ ] **Paso 1: Test (red) — lectura del PDF base**

`tests/test_reconstruir_plantilla.py`:
```python
from pathlib import Path
from unittest.mock import patch
from docx import Document
import subprocess


def _generar_pdf_de_prueba(tmp_path: Path) -> Path:
    docx = tmp_path / "cv.docx"
    doc = Document()
    doc.add_paragraph("Daniel Villalba")
    doc.add_paragraph("Perfil profesional con experiencia en docencia.")
    doc.save(docx)
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", str(docx), "--outdir", str(tmp_path)],
        check=True, capture_output=True,
    )
    return tmp_path / "cv.pdf"


def test_reconstruir_plantilla_lee_cv_base(tmp_path, monkeypatch):
    cv_pdf = _generar_pdf_de_prueba(tmp_path)
    salida_docx = tmp_path / "plantilla.docx"
    salida_pdf_pulido = tmp_path / "cv_pulido.pdf"

    respuesta_simulada = (
        '{"version_pulida": "Daniel Villalba\\nPerfil profesional con experiencia en docencia.",'
        '"version_con_placeholders": "Daniel Villalba\\n{{PERFIL}}",'
        '"cambios_realizados": [],'
        '"advertencias": []}'
    )

    with patch("reconstruir_plantilla.ClienteClaude") as mock_cliente_cls:
        cliente = mock_cliente_cls.return_value
        cliente.preguntar.return_value = (respuesta_simulada, 0.01)

        from reconstruir_plantilla import ejecutar
        ejecutar(
            cv_pdf=cv_pdf,
            salida_docx=salida_docx,
            salida_pdf=salida_pdf_pulido,
            api_key="sk-test",
            confirmar=lambda _: True,
        )

    assert salida_docx.exists()
    assert salida_pdf_pulido.exists()
    doc = Document(salida_docx)
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "{{PERFIL}}" in texto
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_reconstruir_plantilla.py -v
```

- [ ] **Paso 3: Implementar `reconstruir_plantilla.py`**

```python
"""Pule el CV base con Claude y produce plantilla.docx + cv_pulido.pdf.

Uso:
    python reconstruir_plantilla.py
"""
import json
from pathlib import Path
from typing import Callable

from docx import Document

from modulos.cliente_claude import ClienteClaude
from modulos.config import cargar_config
from modulos.pdf_conversor import convertir_docx_a_pdf
from modulos.pdf_lector import leer_pdf

RUTA_CV_BASE = Path("data/cv_base.pdf")
RUTA_SALIDA_DOCX = Path("data/plantilla_base.docx")
RUTA_SALIDA_PDF = Path("data/cv_base_polished.pdf")
RUTA_PROMPT = Path("prompts/pulir_cv.txt")


def _texto_a_docx(texto: str, salida: Path) -> None:
    """Convierte texto plano (con \\n como saltos) a un DOCX simple."""
    doc = Document()
    for parrafo in texto.split("\n"):
        doc.add_paragraph(parrafo)
    salida.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(salida))


def ejecutar(
    cv_pdf: Path = RUTA_CV_BASE,
    salida_docx: Path = RUTA_SALIDA_DOCX,
    salida_pdf: Path = RUTA_SALIDA_PDF,
    api_key: str | None = None,
    confirmar: Callable[[dict], bool] = None,
) -> None:
    """Pule el CV. `confirmar` recibe el dict de respuesta de Claude y devuelve True para guardar."""
    if api_key is None:
        config = cargar_config()
        api_key = config["ANTHROPIC_API_KEY"]

    if not cv_pdf.exists():
        raise FileNotFoundError(
            f"No se encontró {cv_pdf}. Coloca tu HV en esa ruta antes de correr."
        )

    texto_cv = leer_pdf(cv_pdf)
    sistema = RUTA_PROMPT.read_text(encoding="utf-8")
    cliente = ClienteClaude(api_key=api_key)
    respuesta, costo = cliente.preguntar(sistema=sistema, usuario=texto_cv, max_tokens=8000)

    # Limpiar code fence si Claude lo envolvió
    raw = respuesta.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    datos = json.loads(raw.strip())

    if confirmar is not None and not confirmar(datos):
        print("Cancelado por el usuario. No se guardó nada.")
        return

    # Guardar plantilla con placeholders
    _texto_a_docx(datos["version_con_placeholders"], salida_docx)

    # Guardar versión pulida (DOCX → PDF)
    docx_pulido = salida_pdf.with_suffix(".docx")
    _texto_a_docx(datos["version_pulida"], docx_pulido)
    convertir_docx_a_pdf(docx_pulido, salida_pdf)
    docx_pulido.unlink(missing_ok=True)

    print(f"Plantilla guardada en {salida_docx}")
    print(f"Version pulida guardada en {salida_pdf}")
    print(f"Costo de la operación: ${costo:.4f} USD")


def _confirmar_interactivo(datos: dict) -> bool:
    print("\n=== Cambios propuestos por Claude ===")
    for cambio in datos.get("cambios_realizados", []):
        print(f"  - {cambio}")
    if datos.get("advertencias"):
        print("\n=== Advertencias ===")
        for adv in datos["advertencias"]:
            print(f"  ⚠ {adv}")
    respuesta = input("\n¿Aceptas estos cambios y guardas la plantilla? [s/N]: ").strip().lower()
    return respuesta == "s"


if __name__ == "__main__":
    ejecutar(confirmar=_confirmar_interactivo)
```

- [ ] **Paso 4: Correr y ver pasar**

```powershell
pytest tests/test_reconstruir_plantilla.py -v
```

Expected: 1 PASS.

- [ ] **Paso 5: Commit**

```powershell
git add reconstruir_plantilla.py tests/test_reconstruir_plantilla.py
git commit -m "feat(plantilla): comando reconstruir_plantilla.py interactivo"
```

---

## Tarea 18: Detección de hash del CV base (para invalidar plantilla cuando cambia)

**Files:**
- Modify: `modulos/db.py`
- Test: `tests/test_hash_cv.py`

- [ ] **Paso 1: Test (red)**

`tests/test_hash_cv.py`:
```python
from pathlib import Path
from modulos.db import inicializar_db, guardar_hash_cv, hash_cv_actual


def test_guardar_y_leer_hash(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    assert hash_cv_actual(bd) is None
    guardar_hash_cv(bd, "abc123")
    assert hash_cv_actual(bd) == "abc123"
    guardar_hash_cv(bd, "def456")
    assert hash_cv_actual(bd) == "def456"
```

- [ ] **Paso 2: Correr y ver fallar**

```powershell
pytest tests/test_hash_cv.py -v
```

- [ ] **Paso 3: Modificar `modulos/schema.sql` agregando tabla `metadatos`**

Agregar al final de `modulos/schema.sql`:

```sql
-- Tabla de metadatos clave-valor (para hash del CV, versión, etc.)
CREATE TABLE IF NOT EXISTS metadatos (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

- [ ] **Paso 4: Agregar funciones a `modulos/db.py`**

```python
def guardar_hash_cv(ruta_bd, hash_valor: str) -> None:
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            """INSERT INTO metadatos (clave, valor) VALUES ('hash_cv', ?)
               ON CONFLICT(clave) DO UPDATE
               SET valor = excluded.valor, fecha_actualizacion = CURRENT_TIMESTAMP""",
            (hash_valor,),
        )
        conn.commit()
    finally:
        conn.close()


def hash_cv_actual(ruta_bd) -> str | None:
    conn = conectar(ruta_bd)
    try:
        row = conn.execute("SELECT valor FROM metadatos WHERE clave = 'hash_cv'").fetchone()
        return row["valor"] if row else None
    finally:
        conn.close()
```

- [ ] **Paso 5: Correr y ver pasar**

```powershell
pytest tests/test_hash_cv.py -v
```

Expected: 1 PASS.

- [ ] **Paso 6: Modificar `reconstruir_plantilla.py` para guardar el hash**

Agregar en `reconstruir_plantilla.py` al inicio:

```python
import hashlib
from modulos.db import guardar_hash_cv
```

Y dentro de `ejecutar`, después de `convertir_docx_a_pdf(docx_pulido, salida_pdf)`:

```python
    hash_pdf = hashlib.sha256(cv_pdf.read_bytes()).hexdigest()
    bd_path = Path("data/colegios.db")
    if bd_path.exists():
        guardar_hash_cv(bd_path, hash_pdf)
```

- [ ] **Paso 7: Commit**

```powershell
git add modulos/schema.sql modulos/db.py reconstruir_plantilla.py tests/test_hash_cv.py
git commit -m "feat(plantilla): trackear hash del CV base para detectar cambios"
```

---

## Tarea 19: Smoke test end-to-end con el CV real

**Files:**
- (Sin código nuevo, solo verificación manual)

- [ ] **Paso 1: Copiar tu CV real**

```powershell
Copy-Item "C:/Users/elrug/OneDrive/Escritorio/HOJA DE VIDA MAESTRÍA actulizada.pdf" "data/cv_base.pdf"
```

- [ ] **Paso 2: Crear `config/.env` con tu API key**

```powershell
Copy-Item config/.env.example config/.env
notepad config/.env
```

Reemplaza `sk-ant-api03-...` con tu API key real de Anthropic. Guarda y cierra.

- [ ] **Paso 3: Correr `init_db.py`**

```powershell
python init_db.py
```

Expected: "Base de datos lista en C:\Users\elrug\cv-colegios\data\colegios.db".

- [ ] **Paso 4: Correr `reconstruir_plantilla.py`**

```powershell
python reconstruir_plantilla.py
```

Expected: imprime los cambios que Claude propone, te pregunta si aceptas. Tipea `s` y Enter.

Verifica:
- `data/plantilla_base.docx` existe y al abrirlo en Word/LibreOffice contiene `{{PERFIL}}` y `{{EXP_1_TITULO}}` etc.
- `data/cv_base_polished.pdf` existe y al abrirlo se ve tu CV con los typos corregidos.

- [ ] **Paso 5: Inspeccionar BD con DB Browser**

Abre `data/colegios.db` con DB Browser for SQLite. Verifica:
- Las 4 tablas existen: `colegios`, `borradores`, `registro_ejecuciones`, `metadatos`.
- En `metadatos`, hay una fila con `clave='hash_cv'` y un hash sha256.

- [ ] **Paso 6: Correr toda la suite de tests**

```powershell
pytest -v
```

Expected: todos los tests PASS (≈22-25 tests).

- [ ] **Paso 7: Commit del estado verificado**

```powershell
git add docs/
git commit --allow-empty -m "checkpoint: Plan 1 completado y verificado E2E"
git tag v0.1-cimientos
```

---

## Verificación final del Plan 1

Cuando termines:

- [ ] Carpetas creadas: `data/`, `modulos/`, `prompts/`, `config/`, `tests/`
- [ ] Archivos clave existen:
  - `data/colegios.db` (con 4 tablas)
  - `data/plantilla_base.docx` (con placeholders)
  - `data/cv_base_polished.pdf` (CV pulido)
  - `config/.env` (con API key real, NO versionado)
- [ ] Suite de tests pasa: `pytest -v` muestra todos verdes
- [ ] Git: rama `main` con commits granulares y un tag `v0.1-cimientos`
- [ ] Manualmente verificado: tu CV pulido se ve bien al abrirlo

Si todo lo anterior se cumple, el **Plan 1 está completo**. Avísame y escribo el **Plan 2** (Descubrimiento + Enriquecimiento).

---

## Notas para el implementador

- **Si un test falla:** lee el mensaje de error, no asumas. Pregunta a Claude o reporta el log.
- **Si LibreOffice no convierte:** verifica que `soffice --version` funcione en PowerShell. Si no, reinstala LibreOffice marcando "Add to PATH".
- **Si Claude devuelve JSON malformado:** mira los logs de la respuesta cruda; ajusta `prompts/pulir_cv.txt` si es necesario.
- **Si quieres regenerar la plantilla:** vuelve a correr `python reconstruir_plantilla.py` (sobrescribe los archivos de salida).
- **Costos esperados de este plan:** $0.10–$0.30 USD en API (una sola llamada para pulir el CV).
