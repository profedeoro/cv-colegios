# Plan 2 — Descubrimiento de colegios

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el módulo `descubrir` que pobla la BD con colegios privados de Bogotá, Antioquia y Barranquilla a partir de 5 fuentes: el directorio del Ministerio de Educación (MEN), las páginas de miembros de UNCOLI, CONACED y ASCOLPEM, y la API de Google Custom Search.

**Architecture:** Pipeline modular: cada fuente es un módulo independiente en `modulos/scrapers/` que devuelve una lista de `ColegioInfo` (dataclass). El orquestador `modulos/descubrir.py` los llama en orden y usa `insertar_colegio` (ya existe) para guardar en SQLite con dedup automática. Sin `playwright` por ahora — solo `httpx + selectolax`. Si una fuente falla, las demás siguen.

**Tech Stack:** Python 3.11+, httpx (HTTP client), selectolax (parser HTML rápido), dnspython (no se usa en Plan 2 pero se prepara para Plan 3), sqlite3 (stdlib), pytest, pytest-httpx (mock de respuestas HTTP).

**Spec referenciado:** `docs/superpowers/specs/2026-05-05-cv-colegios-design.md` — sección 4.1.

---

## Roadmap actualizado

| Plan | Producto al terminar | Estado |
|---|---|---|
| 1. Cimientos + plantilla | Plantilla DOCX pulida + BD inicializada | ✅ DONE (33 commits) |
| **2. Descubrimiento (este)** | BD poblada con colegios de 3 regiones, deduplicados | En curso |
| 3. Enriquecimiento | Colegios con email + perfil pedagógico clasificado | Próximo |
| 4. Generación + Envío Gmail | Borradores en Gmail listos para enviar | Después |
| 5. Respuestas + Seguimientos | Loop cerrado con detección + notificaciones | Después |
| 6. Orquestación + Despliegue | Sistema en Programador de Windows funcionando | Final |

---

## Conceptos clave para Daniel

- **HTTP scraping:** Bajamos páginas web con código (no con Chrome). Más rápido pero rompe si el sitio cambia su HTML. Manejamos esto detectando errores y reintentando.
- **Google Custom Search API:** Buscador gratis (100 búsquedas/día) con resultados estructurados (JSON). Diferente del buscador público de Google: requiere clave API + ID del "motor de búsqueda" que tú creas.
- **CSV del MEN:** Tabla pública con TODOS los colegios de Colombia (~30K registros). Bajamos esa tabla, filtramos "no oficial" + nuestras 3 regiones, y nos quedamos con ~3K candidatos.
- **Dedup:** ya implementado en Plan 1 (`insertar_colegio` en `modulos/db.py`). Si MEN encuentra "Colegio San José Bogotá" y luego UNCOLI también lo encuentra, la BD acumula `fuente="MEN,UNCOLI"` en una sola fila.

---

## Estructura de archivos a crear

```
modulos/
├── http_cliente.py             ← wrapper httpx con retry + user-agent + timeout
├── descubrir.py                ← orquestador (Tarea 11)
└── scrapers/
    ├── __init__.py
    ├── tipos.py                ← dataclass ColegioInfo (compartida)
    ├── men.py                  ← parsea CSV del MEN (Tarea 5)
    ├── uncoli.py               ← scrape miembros UNCOLI (Tarea 6)
    ├── conaced.py              ← scrape miembros CONACED (Tarea 7)
    ├── ascolpem.py             ← scrape miembros ASCOLPEM (Tarea 8)
    └── google_cse.py           ← Custom Search API (Tarea 9)

correr_modulo.py                ← CLI: `python correr_modulo.py descubrir` (Tarea 12)

config/queries_google.json      ← lista de búsquedas a correr (Tarea 9)

data/raw/                       ← (gitignored) datos descargados manualmente del MEN

prompts/                        ← (sin cambios en Plan 2)
```

---

## Tarea 0: Daniel hace setup de Google Cloud Console (manual, ~15 min)

Esto debe estar listo ANTES de Tarea 9, pero puedes hacerlo en paralelo mientras los sub-agentes trabajan en Tareas 1-8.

- [ ] **Paso 1: Crear proyecto en Google Cloud Console**

1. Abre https://console.cloud.google.com
2. Inicia sesión con tu cuenta de Google.
3. Arriba a la izquierda, donde dice "Select a project", click → "New Project".
4. Nombre: `cv-colegios`, Location: déjalo "No organization". Click "Create".
5. Espera ~30 segundos a que se cree, luego selecciónalo en el dropdown superior.

- [ ] **Paso 2: Habilitar Custom Search API**

1. En el menú izquierdo (las 3 rayitas) → "APIs & Services" → "Library".
2. Busca "Custom Search API" → click en el resultado.
3. Click en el botón azul "Enable".

- [ ] **Paso 3: Crear API key**

1. Menú izquierdo → "APIs & Services" → "Credentials".
2. Click en "+ Create Credentials" → "API key".
3. Copia la key que aparece (algo como `AIzaSy...`). Guárdala.
4. (Opcional, recomendado) Click "Edit API key" → en "API restrictions", selecciona "Restrict key" → marca SOLO "Custom Search API" → Save. Esto evita que la key se use para otras APIs si alguien la roba.

- [ ] **Paso 4: Crear el "Search Engine"**

1. Abre https://programmablesearchengine.google.com en una pestaña nueva.
2. Click en "Get Started" o "Add" → crea un nuevo motor:
   - Name: `cv-colegios-search`
   - "What to search?": elige "Search the entire web"
   - Click "Create".
3. En la página del motor recién creado, busca **"Search engine ID"** (también llamado `cx`). Lo copias. Es algo como `017576662512468239146:omuauf_lfve`.

- [ ] **Paso 5: Agregar las 2 claves a `config/.env`**

Abre `C:/Users/elrug/cv-colegios/config/.env` con notepad. Encuentra estas líneas (vacías):

```
GOOGLE_CSE_API_KEY=
GOOGLE_CSE_ENGINE_ID=
```

Y ponles los valores que copiaste en pasos 3 y 4:

```
GOOGLE_CSE_API_KEY=AIzaSy...   (tu key real)
GOOGLE_CSE_ENGINE_ID=01757666...   (tu engine ID real)
```

Guarda con Ctrl+S, cierra notepad. **Avísame cuando termines.** Mientras tanto, los sub-agentes pueden trabajar en las primeras tareas.

---

## Tarea 1: Agregar dependencias y crear estructura de carpetas

**Files:**
- Modify: `requirements.txt`
- Create: `modulos/scrapers/__init__.py`, `modulos/scrapers/tipos.py`
- Create: `data/raw/.gitkeep` (para preservar la carpeta)

- [ ] **Paso 1: Agregar dependencias a `requirements.txt`**

Agrega estas líneas al final de `C:/Users/elrug/cv-colegios/requirements.txt`:

```
httpx>=0.27.0
selectolax>=0.3.21
dnspython>=2.7.0
pytest-httpx>=0.32.0
```

`httpx` ya estaba como transitiva (de anthropic), pero la marcamos explícita.

- [ ] **Paso 2: Instalar las nuevas dependencias**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pip.exe install -r C:/Users/elrug/cv-colegios/requirements.txt
```

Expected: instala selectolax, dnspython, pytest-httpx (httpx ya estaba).

- [ ] **Paso 3: Crear estructura de carpetas**

```bash
mkdir -p C:/Users/elrug/cv-colegios/modulos/scrapers C:/Users/elrug/cv-colegios/data/raw
touch C:/Users/elrug/cv-colegios/modulos/scrapers/__init__.py
touch C:/Users/elrug/cv-colegios/data/raw/.gitkeep
```

- [ ] **Paso 4: Crear `modulos/scrapers/tipos.py`**

```python
"""Tipos compartidos entre scrapers."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ColegioInfo:
    """Información mínima de un colegio descubierto por una fuente.

    Solo contiene lo que las fuentes pueden saber con certeza. El enriquecimiento
    (web, correo, perfil pedagógico) se hace en una fase posterior (Plan 3).
    """
    nombre: str
    ciudad: str
    departamento: str
    fuente: str                     # "MEN", "UNCOLI", "CONACED", "ASCOLPEM", "Google"
    nit: str | None = None          # solo lo tienen MEN; otras fuentes no
    web: str | None = None          # algunas fuentes lo saben (UNCOLI, Google)
```

- [ ] **Paso 5: Verificar pip install y commit**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pytest.exe C:/Users/elrug/cv-colegios/tests/ -v
```

Expected: 63 passed (no regression). Las nuevas deps no rompen nada.

```bash
git -C C:/Users/elrug/cv-colegios add requirements.txt modulos/scrapers/ data/raw/.gitkeep
git -C C:/Users/elrug/cv-colegios commit -m "chore(plan2): dependencias scraping + estructura scrapers/"
```

---

## Tarea 2: Actualizar config para claves opcionales

**Files:**
- Modify: `modulos/config.py`
- Modify: `tests/test_config.py`

Plan 1 hizo `ANTHROPIC_API_KEY` requerida. Las claves de Google CSE son opcionales: solo el módulo `descubrir` las necesita. Si alguien corre `reconstruir_plantilla.py` sin tener Google CSE configurado, debe funcionar igual.

- [ ] **Paso 1: Test (red) — claves opcionales no bloquean cargar_config**

Agregar al final de `C:/Users/elrug/cv-colegios/tests/test_config.py`:

```python
def test_cargar_config_no_falla_sin_google_cse(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-test\n")
    config = cargar_config(env_path=env_file)
    assert "GOOGLE_CSE_API_KEY" not in config or not config["GOOGLE_CSE_API_KEY"]


def test_validar_google_cse_falla_si_falta(tmp_path):
    from modulos.config import validar_google_cse
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-test\n")
    config = cargar_config(env_path=env_file)
    with pytest.raises(ConfigError, match="GOOGLE_CSE"):
        validar_google_cse(config)


def test_validar_google_cse_pasa_si_estan(tmp_path):
    from modulos.config import validar_google_cse
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=sk-test\n"
        "GOOGLE_CSE_API_KEY=AIza-test\n"
        "GOOGLE_CSE_ENGINE_ID=eng-test\n"
    )
    config = cargar_config(env_path=env_file)
    validar_google_cse(config)  # no debe lanzar
```

- [ ] **Paso 2: Run test, see fail**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pytest.exe C:/Users/elrug/cv-colegios/tests/test_config.py -v
```

Expected: ImportError on `validar_google_cse`.

- [ ] **Paso 3: Modificar `modulos/config.py`**

Agregar al final del archivo:

```python
GOOGLE_CSE_REQUERIDAS = ["GOOGLE_CSE_API_KEY", "GOOGLE_CSE_ENGINE_ID"]


def validar_google_cse(config: dict) -> None:
    """Verifica que las claves de Google Custom Search estén presentes.

    Solo llamar desde módulos que realmente las necesiten (descubrir.py).
    """
    faltantes = [k for k in GOOGLE_CSE_REQUERIDAS if not config.get(k)]
    if faltantes:
        raise ConfigError(
            f"Faltan claves de Google Custom Search: {', '.join(faltantes)}. "
            "Configúralas en config/.env (ver instrucciones en plan 2)."
        )
```

- [ ] **Paso 4: Run, see pass**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pytest.exe C:/Users/elrug/cv-colegios/tests/test_config.py -v
```

Expected: 6 PASS (3 prior + 3 new).

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/config.py tests/test_config.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(config): validador opcional para Google CSE"
```

---

## Tarea 3: Cliente HTTP base

**Files:**
- Create: `modulos/http_cliente.py`
- Create: `tests/test_http_cliente.py`

- [ ] **Paso 1: Test (red)**

`tests/test_http_cliente.py`:
```python
import pytest
from modulos.http_cliente import fetch_html, HttpError, USER_AGENT


def test_fetch_html_devuelve_contenido(httpx_mock):
    httpx_mock.add_response(url="https://ejemplo.com/", html="<html><body>Hola</body></html>")
    html = fetch_html("https://ejemplo.com/")
    assert "Hola" in html


def test_fetch_html_envia_user_agent(httpx_mock):
    httpx_mock.add_response(url="https://ejemplo.com/", html="ok")
    fetch_html("https://ejemplo.com/")
    request = httpx_mock.get_request()
    assert request.headers["user-agent"] == USER_AGENT


def test_fetch_html_lanza_error_en_404(httpx_mock):
    httpx_mock.add_response(url="https://ejemplo.com/", status_code=404)
    with pytest.raises(HttpError, match="404"):
        fetch_html("https://ejemplo.com/")


def test_fetch_html_reintenta_en_5xx(httpx_mock):
    # Primer intento falla, segundo intento ok
    httpx_mock.add_response(url="https://ejemplo.com/", status_code=503)
    httpx_mock.add_response(url="https://ejemplo.com/", html="ok")
    html = fetch_html("https://ejemplo.com/", max_reintentos=2)
    assert html == "ok"


def test_fetch_html_falla_despues_de_max_reintentos(httpx_mock):
    httpx_mock.add_response(url="https://ejemplo.com/", status_code=500)
    httpx_mock.add_response(url="https://ejemplo.com/", status_code=500)
    with pytest.raises(HttpError, match="500"):
        fetch_html("https://ejemplo.com/", max_reintentos=2)
```

- [ ] **Paso 2: Run, see fail**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pytest.exe C:/Users/elrug/cv-colegios/tests/test_http_cliente.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Paso 3: Implementar `modulos/http_cliente.py`**

```python
"""Cliente HTTP con retries, timeout y user-agent identificable."""
import time
import httpx

USER_AGENT = "cv-colegios-scraper/1.0 (+research; contact: danedu348@gmail.com)"
TIMEOUT = 15.0


class HttpError(Exception):
    """Error al hacer una petición HTTP."""


def fetch_html(url: str, max_reintentos: int = 3, timeout: float = TIMEOUT) -> str:
    """Descarga el HTML de una URL. Reintenta en errores transitorios (5xx).

    Levanta HttpError en errores definitivos (4xx) o si todos los reintentos fallan.
    """
    headers = {"User-Agent": USER_AGENT}
    ultimo_error = None
    for intento in range(max_reintentos):
        try:
            with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True) as cli:
                resp = cli.get(url)
                if 200 <= resp.status_code < 300:
                    return resp.text
                if 400 <= resp.status_code < 500:
                    raise HttpError(f"HTTP {resp.status_code} en {url}")
                # 5xx: reintenta con backoff
                ultimo_error = HttpError(f"HTTP {resp.status_code} en {url}")
                time.sleep(0.5 * (2 ** intento))
        except httpx.RequestError as e:
            ultimo_error = HttpError(f"Error de red en {url}: {e}")
            time.sleep(0.5 * (2 ** intento))
    raise ultimo_error if ultimo_error else HttpError(f"Falló sin razón clara: {url}")
```

- [ ] **Paso 4: Run, see pass**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pytest.exe C:/Users/elrug/cv-colegios/tests/test_http_cliente.py -v
```

Expected: 5 PASS.

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/http_cliente.py tests/test_http_cliente.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(http): cliente con retry, user-agent y timeout"
```

---

## Tarea 4: Daniel descarga el CSV del MEN (manual, ~5 min)

Este paso es manual porque el endpoint del MEN cambia y a veces requiere captcha/cookies.

- [ ] **Paso 1: Descargar el directorio**

1. Abre https://www.datos.gov.co
2. Busca: `Establecimientos Educativos`
3. Busca el dataset oficial del MEN (suele decir "Establecimientos Educativos del MEN" o similar — el publicado por "MINISTERIO DE EDUCACION NACIONAL").
4. Click en "Exportar" → CSV.
5. Guarda el archivo como `C:/Users/elrug/cv-colegios/data/raw/men_directorio.csv`.

Nota: si no encuentras dataset, alternativa: descarga directamente desde el geoportal del MEN o usa el catálogo SIET. Para Plan 2 lo importante es tener UN CSV con columnas que incluyan: nombre/razón social, departamento, municipio, NIT, naturaleza ("oficial" / "no oficial"), nivel educativo.

- [ ] **Paso 2: Inspeccionar el CSV**

Abre el archivo con Excel o LibreOffice y mira:
- ¿Cuántos registros tiene? (debería ser ~50.000+)
- ¿Qué columnas trae? Anota los nombres EXACTOS de las columnas que tengan: nombre, departamento, municipio, NIT, naturaleza/sector.

Pásame esos nombres de columna cuando termines — los necesito para Tarea 5.

---

## Tarea 5: Scraper del MEN (parsea el CSV)

**Files:**
- Create: `modulos/scrapers/men.py`
- Create: `tests/test_scraper_men.py`
- Create: `tests/fixtures/men_sample.csv` (CSV pequeño para tests)

NOTE: la implementación asume nombres de columna estándar. Si el CSV real tiene otros nombres, hay que ajustar el dict `COLUMNAS` en `men.py`.

- [ ] **Paso 1: Crear fixture de CSV pequeño**

`tests/fixtures/men_sample.csv`:
```csv
NIT,NOMBRE_ESTABLECIMIENTO,MUNICIPIO,DEPARTAMENTO,NATURALEZA,NIVEL
800123456,Colegio San Tarsicio,BOGOTÁ D.C.,BOGOTÁ D.C.,NO OFICIAL,SECUNDARIA
800123457,Liceo Campestre,MEDELLÍN,ANTIOQUIA,NO OFICIAL,SECUNDARIA
800123458,Escuela Pública Norte,BARRANQUILLA,ATLÁNTICO,OFICIAL,PRIMARIA
800123459,Colegio Bilingüe Bay,BARRANQUILLA,ATLÁNTICO,NO OFICIAL,SECUNDARIA
800123460,Escuela Rural,ENVIGADO,ANTIOQUIA,NO OFICIAL,PRIMARIA
800123461,Colegio Privado Cali,CALI,VALLE DEL CAUCA,NO OFICIAL,SECUNDARIA
```

(NIT 800123458 es OFICIAL → debe filtrarse fuera. NIT 800123461 es de Cali → fuera de regiones target.)

```bash
mkdir -p C:/Users/elrug/cv-colegios/tests/fixtures
```

Crear el archivo `tests/fixtures/men_sample.csv` con el contenido de arriba.

- [ ] **Paso 2: Test (red)**

`tests/test_scraper_men.py`:
```python
from pathlib import Path
import pytest
from modulos.scrapers.men import parsear_men, REGIONES_OBJETIVO

FIXTURE = Path(__file__).parent / "fixtures" / "men_sample.csv"


def test_parsear_men_filtra_solo_no_oficiales_de_regiones_objetivo():
    colegios = parsear_men(FIXTURE)
    nombres = [c.nombre for c in colegios]
    # Esperado: 3 colegios (los 3 NO OFICIAL en Bogotá / Antioquia / Atlántico/Barranquilla)
    assert "Colegio San Tarsicio" in nombres
    assert "Liceo Campestre" in nombres
    assert "Colegio Bilingüe Bay" in nombres
    # NO debe incluir oficial ni Cali ni Envigado (Envigado SÍ es Antioquia, debe estar; ajustar)


def test_envigado_es_antioquia_y_se_incluye():
    """Envigado es Antioquia → cualquier colegio no oficial en Envigado debe entrar."""
    colegios = parsear_men(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Escuela Rural" in nombres


def test_barranquilla_se_incluye_pero_resto_de_atlantico_no():
    """De Atlántico solo entra Barranquilla, no otros municipios."""
    # Ampliar fixture en futuro con otro municipio del Atlántico para verificar
    colegios = parsear_men(FIXTURE)
    ciudades = [c.ciudad for c in colegios if c.departamento.upper().startswith("ATL")]
    assert all(c.upper() == "BARRANQUILLA" for c in ciudades)


def test_oficial_se_excluye():
    colegios = parsear_men(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Escuela Pública Norte" not in nombres


def test_otras_regiones_se_excluyen():
    colegios = parsear_men(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Colegio Privado Cali" not in nombres


def test_fuente_es_men():
    colegios = parsear_men(FIXTURE)
    assert all(c.fuente == "MEN" for c in colegios)


def test_nit_se_preserva():
    colegios = parsear_men(FIXTURE)
    nits = {c.nit for c in colegios}
    assert "800123456" in nits


def test_falla_si_csv_no_existe(tmp_path):
    with pytest.raises(FileNotFoundError):
        parsear_men(tmp_path / "no_existe.csv")
```

- [ ] **Paso 3: Run, see fail**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pytest.exe C:/Users/elrug/cv-colegios/tests/test_scraper_men.py -v
```

- [ ] **Paso 4: Implementar `modulos/scrapers/men.py`**

```python
"""Parser del CSV del directorio MEN.

Daniel descarga el CSV manualmente desde datos.gov.co y lo coloca en
data/raw/men_directorio.csv. Esta función lo parsea y filtra los colegios
no oficiales de Bogotá D.C., Antioquia, y Barranquilla (Atlántico).
"""
import csv
from pathlib import Path
from modulos.scrapers.tipos import ColegioInfo

# Departamentos completos: Bogotá y Antioquia (todo).
# Atlántico: solo Barranquilla.
REGIONES_OBJETIVO = {
    "BOGOTÁ D.C.": None,        # None = todos los municipios
    "BOGOTA D.C.": None,        # variante sin acento
    "ANTIOQUIA": None,
    "ATLÁNTICO": {"BARRANQUILLA"},
    "ATLANTICO": {"BARRANQUILLA"},
}

# Si el CSV usa otros nombres de columna, ajustar este mapeo:
COLUMNAS = {
    "nit": ["NIT", "Nit", "nit"],
    "nombre": ["NOMBRE_ESTABLECIMIENTO", "Nombre del Establecimiento", "ESTABLECIMIENTO", "NOMBRE"],
    "municipio": ["MUNICIPIO", "Municipio", "MUNICIPIO_NOMBRE"],
    "departamento": ["DEPARTAMENTO", "Departamento", "DEPARTAMENTO_NOMBRE"],
    "naturaleza": ["NATURALEZA", "Naturaleza", "SECTOR"],
}


def _detectar_columnas(headers: list[str]) -> dict[str, str]:
    """Mapea cada campo lógico al nombre de columna real del CSV."""
    mapeo = {}
    for campo, candidatos in COLUMNAS.items():
        for c in candidatos:
            if c in headers:
                mapeo[campo] = c
                break
        else:
            raise ValueError(f"No encontré ninguna columna válida para '{campo}'. Probé: {candidatos}")
    return mapeo


def _es_region_objetivo(departamento: str, municipio: str) -> bool:
    dep = departamento.strip().upper()
    mun = municipio.strip().upper()
    if dep not in REGIONES_OBJETIVO:
        return False
    municipios_permitidos = REGIONES_OBJETIVO[dep]
    if municipios_permitidos is None:
        return True
    return mun in municipios_permitidos


def parsear_men(ruta_csv: Path | str) -> list[ColegioInfo]:
    """Parsea el CSV del MEN y devuelve los colegios no oficiales de las regiones objetivo."""
    ruta = Path(ruta_csv)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró {ruta}. Descárgalo de datos.gov.co.")

    colegios = []
    with ruta.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        col = _detectar_columnas(reader.fieldnames or [])
        for fila in reader:
            naturaleza = fila[col["naturaleza"]].strip().upper()
            if "NO OFICIAL" not in naturaleza and "PRIVAD" not in naturaleza:
                continue
            departamento = fila[col["departamento"]].strip()
            municipio = fila[col["municipio"]].strip()
            if not _es_region_objetivo(departamento, municipio):
                continue
            colegios.append(ColegioInfo(
                nombre=fila[col["nombre"]].strip(),
                ciudad=municipio,
                departamento=departamento,
                fuente="MEN",
                nit=fila[col["nit"]].strip() or None,
            ))
    return colegios
```

- [ ] **Paso 5: Run, see pass**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pytest.exe C:/Users/elrug/cv-colegios/tests/test_scraper_men.py -v
```

Expected: 8 PASS.

- [ ] **Paso 6: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/scrapers/men.py tests/test_scraper_men.py tests/fixtures/men_sample.csv
git -C C:/Users/elrug/cv-colegios commit -m "feat(scrapers): parser del CSV del MEN con filtros de región"
```

---

## Tarea 6: Scraper UNCOLI

**Files:**
- Create: `modulos/scrapers/uncoli.py`
- Create: `tests/test_scraper_uncoli.py`
- Create: `tests/fixtures/uncoli_sample.html`

UNCOLI publica su lista de miembros en su sitio web. Usaremos `httpx` + `selectolax` para parsearlo. Como la URL exacta y el HTML pueden cambiar, dejamos parametrizable la URL y el selector CSS.

- [ ] **Paso 1: Crear fixture HTML**

`tests/fixtures/uncoli_sample.html` (copia exacta de un fragmento de la página de miembros UNCOLI; este es ilustrativo):
```html
<!DOCTYPE html>
<html>
<body>
<div class="member-list">
  <article class="member">
    <h3 class="member-name">COLEGIO ANGLO COLOMBIANO</h3>
    <a class="member-link" href="https://www.anglocolombiano.edu.co/">Visitar sitio</a>
  </article>
  <article class="member">
    <h3 class="member-name">COLEGIO LOS NOGALES</h3>
    <a class="member-link" href="https://www.nogales.edu.co/">Visitar sitio</a>
  </article>
  <article class="member">
    <h3 class="member-name">GIMNASIO MODERNO</h3>
    <a class="member-link" href="https://www.gimnasiomoderno.edu.co/">Visitar sitio</a>
  </article>
</div>
</body>
</html>
```

NOTA: el HTML real de UNCOLI es diferente. El implementador debe inspeccionar https://www.uncoli.org/colegios-asociados/ con DevTools del navegador para identificar los selectores CSS reales antes de ejecutar contra producción. Para los tests usamos este fixture controlado.

- [ ] **Paso 2: Test (red)**

`tests/test_scraper_uncoli.py`:
```python
from pathlib import Path
import pytest
from modulos.scrapers.uncoli import parsear_html_uncoli, scrape_uncoli

FIXTURE = (Path(__file__).parent / "fixtures" / "uncoli_sample.html").read_text(encoding="utf-8")


def test_parsear_extrae_nombres():
    colegios = parsear_html_uncoli(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "COLEGIO ANGLO COLOMBIANO" in nombres
    assert "COLEGIO LOS NOGALES" in nombres
    assert "GIMNASIO MODERNO" in nombres


def test_parsear_asigna_ciudad_bogota_y_departamento():
    """UNCOLI agrupa colegios de Bogotá. Asumimos ciudad=Bogotá, departamento=Bogotá D.C."""
    colegios = parsear_html_uncoli(FIXTURE)
    assert all(c.ciudad == "Bogotá" for c in colegios)
    assert all(c.departamento == "Bogotá D.C." for c in colegios)


def test_parsear_extrae_web_si_disponible():
    colegios = parsear_html_uncoli(FIXTURE)
    web_anglo = next(c.web for c in colegios if "ANGLO" in c.nombre)
    assert web_anglo == "https://www.anglocolombiano.edu.co/"


def test_parsear_fuente_es_uncoli():
    colegios = parsear_html_uncoli(FIXTURE)
    assert all(c.fuente == "UNCOLI" for c in colegios)


def test_scrape_uncoli_usa_http(httpx_mock):
    httpx_mock.add_response(
        url="https://www.uncoli.org/colegios-asociados/",
        html=FIXTURE,
    )
    colegios = scrape_uncoli()
    assert len(colegios) == 3
```

- [ ] **Paso 3: Run, see fail**

- [ ] **Paso 4: Implementar `modulos/scrapers/uncoli.py`**

```python
"""Scraper de la lista de miembros de UNCOLI (Unión de Colegios Internacionales)."""
from selectolax.parser import HTMLParser
from modulos.http_cliente import fetch_html
from modulos.scrapers.tipos import ColegioInfo

URL_UNCOLI = "https://www.uncoli.org/colegios-asociados/"

# Selector CSS — ajustar si UNCOLI cambia su HTML.
# El implementador debe verificar este selector contra la página real antes de usar en prod.
SELECTOR_MIEMBRO = "article.member, .member-list .member"
SELECTOR_NOMBRE = "h3.member-name, .member-name"
SELECTOR_LINK = "a.member-link, .member-link"


def parsear_html_uncoli(html: str) -> list[ColegioInfo]:
    """Extrae colegios de un HTML de la página de miembros UNCOLI."""
    tree = HTMLParser(html)
    colegios = []
    for nodo_miembro in tree.css(SELECTOR_MIEMBRO):
        nombre_node = nodo_miembro.css_first(SELECTOR_NOMBRE)
        if not nombre_node:
            continue
        nombre = nombre_node.text(strip=True)
        link_node = nodo_miembro.css_first(SELECTOR_LINK)
        web = link_node.attributes.get("href") if link_node else None
        colegios.append(ColegioInfo(
            nombre=nombre,
            ciudad="Bogotá",
            departamento="Bogotá D.C.",
            fuente="UNCOLI",
            web=web,
        ))
    return colegios


def scrape_uncoli() -> list[ColegioInfo]:
    """Descarga la página de UNCOLI y extrae los colegios."""
    html = fetch_html(URL_UNCOLI)
    return parsear_html_uncoli(html)
```

- [ ] **Paso 5: Run, see pass**

Expected: 5 PASS.

- [ ] **Paso 6: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/scrapers/uncoli.py tests/test_scraper_uncoli.py tests/fixtures/uncoli_sample.html
git -C C:/Users/elrug/cv-colegios commit -m "feat(scrapers): UNCOLI miembros con HTTP + selectolax"
```

---

## Tarea 7: Scraper CONACED

Idéntico patrón a Tarea 6. CONACED es la asociación de colegios católicos.

**Files:**
- Create: `modulos/scrapers/conaced.py`
- Create: `tests/test_scraper_conaced.py`
- Create: `tests/fixtures/conaced_sample.html`

- [ ] **Paso 1: Fixture HTML**

`tests/fixtures/conaced_sample.html`:
```html
<!DOCTYPE html>
<html>
<body>
<ul class="colegios-list">
  <li class="colegio-item" data-ciudad="Bogotá" data-depto="Bogotá D.C.">
    <span class="nombre">Colegio Calasanz Bogotá</span>
  </li>
  <li class="colegio-item" data-ciudad="Medellín" data-depto="Antioquia">
    <span class="nombre">Colegio San José de las Vegas</span>
  </li>
  <li class="colegio-item" data-ciudad="Cali" data-depto="Valle del Cauca">
    <span class="nombre">Colegio Berchmans</span>
  </li>
</ul>
</body>
</html>
```

- [ ] **Paso 2: Test (red)**

`tests/test_scraper_conaced.py`:
```python
from pathlib import Path
from modulos.scrapers.conaced import parsear_html_conaced, scrape_conaced
from modulos.scrapers.tipos import ColegioInfo

FIXTURE = (Path(__file__).parent / "fixtures" / "conaced_sample.html").read_text(encoding="utf-8")


def test_parsear_extrae_colegios_con_ciudad_y_depto():
    colegios = parsear_html_conaced(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Colegio Calasanz Bogotá" in nombres


def test_filtra_solo_regiones_objetivo():
    colegios = parsear_html_conaced(FIXTURE)
    nombres = [c.nombre for c in colegios]
    # Cali NO debe estar
    assert "Colegio Berchmans" not in nombres
    # Bogotá y Medellín SÍ
    assert "Colegio Calasanz Bogotá" in nombres
    assert "Colegio San José de las Vegas" in nombres


def test_scrape_usa_http(httpx_mock):
    httpx_mock.add_response(url="https://www.conaced.edu.co/colegios", html=FIXTURE)
    colegios = scrape_conaced()
    assert len(colegios) == 2
```

- [ ] **Paso 3: Run, see fail**

- [ ] **Paso 4: Implementar `modulos/scrapers/conaced.py`**

```python
"""Scraper de la lista de miembros de CONACED."""
from selectolax.parser import HTMLParser
from modulos.http_cliente import fetch_html
from modulos.scrapers.tipos import ColegioInfo

URL_CONACED = "https://www.conaced.edu.co/colegios"
SELECTOR_ITEM = "li.colegio-item, .colegios-list li"
SELECTOR_NOMBRE = ".nombre, .colegio-nombre"

DEPARTAMENTOS_OBJETIVO = {"Bogotá D.C.", "Antioquia", "Atlántico"}
CIUDADES_ATLANTICO = {"Barranquilla"}


def _es_region_objetivo(departamento: str, ciudad: str) -> bool:
    if departamento not in DEPARTAMENTOS_OBJETIVO:
        return False
    if departamento == "Atlántico" and ciudad not in CIUDADES_ATLANTICO:
        return False
    return True


def parsear_html_conaced(html: str) -> list[ColegioInfo]:
    tree = HTMLParser(html)
    colegios = []
    for item in tree.css(SELECTOR_ITEM):
        nombre_node = item.css_first(SELECTOR_NOMBRE)
        if not nombre_node:
            continue
        nombre = nombre_node.text(strip=True)
        ciudad = item.attributes.get("data-ciudad", "")
        depto = item.attributes.get("data-depto", "")
        if not _es_region_objetivo(depto, ciudad):
            continue
        colegios.append(ColegioInfo(
            nombre=nombre,
            ciudad=ciudad,
            departamento=depto,
            fuente="CONACED",
        ))
    return colegios


def scrape_conaced() -> list[ColegioInfo]:
    html = fetch_html(URL_CONACED)
    return parsear_html_conaced(html)
```

- [ ] **Paso 5: Run, see pass**

Expected: 3 PASS.

- [ ] **Paso 6: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/scrapers/conaced.py tests/test_scraper_conaced.py tests/fixtures/conaced_sample.html
git -C C:/Users/elrug/cv-colegios commit -m "feat(scrapers): CONACED miembros"
```

---

## Tarea 8: Scraper ASCOLPEM

Mismo patrón. Si ASCOLPEM no tiene un sitio web público con lista de miembros (caso real), el scraper devuelve lista vacía y el orquestador lo trata como fuente "no productiva". Esto es aceptable porque las otras 4 fuentes ya cubren bien.

**Files:**
- Create: `modulos/scrapers/ascolpem.py`
- Create: `tests/test_scraper_ascolpem.py`
- Create: `tests/fixtures/ascolpem_sample.html`

- [ ] **Paso 1: Fixture HTML**

`tests/fixtures/ascolpem_sample.html`:
```html
<!DOCTYPE html>
<html>
<body>
<table id="afiliados">
  <tr><th>Colegio</th><th>Ciudad</th><th>Departamento</th></tr>
  <tr><td>Colegio Andino Cartagena</td><td>Cartagena</td><td>Bolívar</td></tr>
  <tr><td>Liceo Pino Verde</td><td>Pereira</td><td>Risaralda</td></tr>
  <tr><td>Colegio Marymount</td><td>Medellín</td><td>Antioquia</td></tr>
</table>
</body>
</html>
```

- [ ] **Paso 2: Test (red)**

`tests/test_scraper_ascolpem.py`:
```python
from pathlib import Path
from modulos.scrapers.ascolpem import parsear_html_ascolpem, scrape_ascolpem

FIXTURE = (Path(__file__).parent / "fixtures" / "ascolpem_sample.html").read_text(encoding="utf-8")


def test_parsear_extrae_de_tabla():
    colegios = parsear_html_ascolpem(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Colegio Marymount" in nombres


def test_filtra_regiones_objetivo():
    colegios = parsear_html_ascolpem(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Colegio Andino Cartagena" not in nombres  # Bolívar fuera
    assert "Liceo Pino Verde" not in nombres  # Risaralda fuera
    assert "Colegio Marymount" in nombres  # Antioquia dentro


def test_scrape_devuelve_lista_vacia_en_404(httpx_mock):
    """Si la URL de ASCOLPEM no existe o cambia, el scraper no debe romper el pipeline."""
    httpx_mock.add_response(
        url="https://www.ascolpem.com/afiliados",
        status_code=404,
    )
    colegios = scrape_ascolpem()
    assert colegios == []
```

- [ ] **Paso 3: Run, see fail**

- [ ] **Paso 4: Implementar `modulos/scrapers/ascolpem.py`**

```python
"""Scraper de ASCOLPEM. Tolerante a fallos: devuelve [] si la URL no existe."""
from selectolax.parser import HTMLParser
from modulos.http_cliente import fetch_html, HttpError
from modulos.scrapers.tipos import ColegioInfo

URL_ASCOLPEM = "https://www.ascolpem.com/afiliados"

DEPARTAMENTOS_OBJETIVO = {"Bogotá D.C.", "Antioquia", "Atlántico"}
CIUDADES_ATLANTICO = {"Barranquilla"}


def _es_region_objetivo(departamento: str, ciudad: str) -> bool:
    if departamento not in DEPARTAMENTOS_OBJETIVO:
        return False
    if departamento == "Atlántico" and ciudad not in CIUDADES_ATLANTICO:
        return False
    return True


def parsear_html_ascolpem(html: str) -> list[ColegioInfo]:
    tree = HTMLParser(html)
    colegios = []
    for fila in tree.css("table#afiliados tr"):
        celdas = fila.css("td")
        if len(celdas) < 3:
            continue  # encabezado o fila vacía
        nombre = celdas[0].text(strip=True)
        ciudad = celdas[1].text(strip=True)
        departamento = celdas[2].text(strip=True)
        if not _es_region_objetivo(departamento, ciudad):
            continue
        colegios.append(ColegioInfo(
            nombre=nombre,
            ciudad=ciudad,
            departamento=departamento,
            fuente="ASCOLPEM",
        ))
    return colegios


def scrape_ascolpem() -> list[ColegioInfo]:
    """Tolerante: devuelve [] si la URL falla."""
    try:
        html = fetch_html(URL_ASCOLPEM)
    except HttpError:
        return []
    return parsear_html_ascolpem(html)
```

- [ ] **Paso 5: Run, see pass**

Expected: 3 PASS.

- [ ] **Paso 6: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/scrapers/ascolpem.py tests/test_scraper_ascolpem.py tests/fixtures/ascolpem_sample.html
git -C C:/Users/elrug/cv-colegios commit -m "feat(scrapers): ASCOLPEM tolerante a fallos"
```

---

## Tarea 9: Google Custom Search

**Files:**
- Create: `modulos/scrapers/google_cse.py`
- Create: `config/queries_google.json`
- Create: `tests/test_scraper_google.py`

- [ ] **Paso 1: Crear lista de queries**

`config/queries_google.json`:
```json
{
  "queries": [
    "colegio bilingüe Bogotá site:.edu.co",
    "colegio campestre Bogotá site:.edu.co",
    "colegio Calasanz Bogotá site:.edu.co",
    "colegio bilingüe Medellín site:.edu.co",
    "colegio campestre Antioquia site:.edu.co",
    "colegio bilingüe Barranquilla site:.edu.co",
    "colegio Marymount Antioquia site:.edu.co",
    "colegio gimnasio Bogotá site:.edu.co",
    "colegio liceo Bogotá site:.edu.co",
    "colegio internacional Antioquia site:.edu.co"
  ]
}
```

- [ ] **Paso 2: Test (red)**

`tests/test_scraper_google.py`:
```python
import json
from pathlib import Path
import pytest
from modulos.scrapers.google_cse import buscar_google, queries_a_colegios


def test_buscar_google_arma_url_correcta(httpx_mock):
    httpx_mock.add_response(
        url__regex=r"https://www\.googleapis\.com/customsearch/v1.*",
        json={
            "items": [
                {"title": "Colegio San X - Bogotá", "link": "https://sanx.edu.co/", "snippet": "..."},
                {"title": "Colegio Y", "link": "https://y.edu.co/", "snippet": "..."},
            ]
        },
    )
    resultados = buscar_google(
        query="colegio site:.edu.co",
        api_key="AIza-test",
        engine_id="eng-test",
    )
    assert len(resultados) == 2
    assert resultados[0]["link"] == "https://sanx.edu.co/"


def test_buscar_google_devuelve_vacio_si_no_hay_items(httpx_mock):
    httpx_mock.add_response(
        url__regex=r"https://www\.googleapis\.com/customsearch/v1.*",
        json={},
    )
    resultados = buscar_google(query="x", api_key="k", engine_id="e")
    assert resultados == []


def test_queries_a_colegios_convierte_resultados(httpx_mock):
    """Los items de Google Search se convierten a ColegioInfo con ciudad inferida."""
    httpx_mock.add_response(
        url__regex=r".*",
        json={
            "items": [
                {"title": "Colegio Bilingüe Bay - Barranquilla", "link": "https://bay.edu.co/"},
            ]
        },
    )
    colegios = queries_a_colegios(
        queries=["colegio bilingüe Barranquilla site:.edu.co"],
        api_key="k",
        engine_id="e",
        max_por_query=5,
    )
    assert len(colegios) >= 1
    assert "Bay" in colegios[0].nombre
    assert colegios[0].fuente == "Google"
```

- [ ] **Paso 3: Run, see fail**

- [ ] **Paso 4: Implementar `modulos/scrapers/google_cse.py`**

```python
"""Wrapper sobre la API de Google Custom Search.

Cuota gratis: 100 consultas/día. Cada consulta devuelve hasta 10 resultados.
"""
import re
import httpx
from modulos.scrapers.tipos import ColegioInfo

URL_API = "https://www.googleapis.com/customsearch/v1"

# Heurística: detectar ciudad en el título de un resultado.
PATRONES_CIUDAD = [
    (re.compile(r"\bBogot[áa]\b", re.IGNORECASE), ("Bogotá", "Bogotá D.C.")),
    (re.compile(r"\bMedell[íi]n\b", re.IGNORECASE), ("Medellín", "Antioquia")),
    (re.compile(r"\bEnvigado\b", re.IGNORECASE), ("Envigado", "Antioquia")),
    (re.compile(r"\bSabaneta\b", re.IGNORECASE), ("Sabaneta", "Antioquia")),
    (re.compile(r"\bRionegro\b", re.IGNORECASE), ("Rionegro", "Antioquia")),
    (re.compile(r"\bBarranquilla\b", re.IGNORECASE), ("Barranquilla", "Atlántico")),
]


def buscar_google(query: str, api_key: str, engine_id: str, num: int = 10) -> list[dict]:
    """Hace una búsqueda y devuelve los items (lista de dicts con 'title', 'link', etc.)."""
    params = {"q": query, "key": api_key, "cx": engine_id, "num": num}
    with httpx.Client(timeout=15.0) as cli:
        resp = cli.get(URL_API, params=params)
        resp.raise_for_status()
        return resp.json().get("items", [])


def _inferir_ubicacion(texto: str) -> tuple[str, str] | None:
    """Detecta ciudad+departamento en un texto. Devuelve (ciudad, depto) o None."""
    for patron, (ciudad, depto) in PATRONES_CIUDAD:
        if patron.search(texto):
            return ciudad, depto
    return None


def queries_a_colegios(
    queries: list[str],
    api_key: str,
    engine_id: str,
    max_por_query: int = 10,
) -> list[ColegioInfo]:
    """Corre todas las queries y consolida resultados como ColegioInfo."""
    colegios: list[ColegioInfo] = []
    for q in queries:
        try:
            items = buscar_google(q, api_key, engine_id, num=max_por_query)
        except (httpx.HTTPError, httpx.RequestError):
            continue
        for item in items:
            titulo = item.get("title", "").strip()
            link = item.get("link", "").strip()
            ubicacion = _inferir_ubicacion(titulo) or _inferir_ubicacion(q)
            if not ubicacion:
                continue  # no logramos inferir ciudad → descartamos
            ciudad, depto = ubicacion
            colegios.append(ColegioInfo(
                nombre=titulo,
                ciudad=ciudad,
                departamento=depto,
                fuente="Google",
                web=link or None,
            ))
    return colegios
```

- [ ] **Paso 5: Run, see pass**

Expected: 3 PASS.

- [ ] **Paso 6: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/scrapers/google_cse.py config/queries_google.json tests/test_scraper_google.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(scrapers): wrapper de Google Custom Search API"
```

---

## Tarea 10: Logger en BD (registro_ejecuciones)

**Files:**
- Modify: `modulos/db.py` — agregar `registrar_ejecucion`
- Test: `tests/test_db_registro.py`

Cada vez que un módulo corre, deja una fila en `registro_ejecuciones`. Esto se usa para idempotencia (saber si ya corrió hoy) y para auditoría.

- [ ] **Paso 1: Test (red)**

`tests/test_db_registro.py`:
```python
from modulos.db import inicializar_db, registrar_ejecucion, ultima_ejecucion_ok


def test_registrar_ejecucion_ok(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    registrar_ejecucion(bd, modulo="descubrir", duracion_segundos=12.5,
                        estado="ok", colegios_procesados=42, costo_api_usd=0.05)
    from modulos.db import conectar
    conn = conectar(bd)
    row = conn.execute("SELECT * FROM registro_ejecuciones").fetchone()
    conn.close()
    assert row["modulo"] == "descubrir"
    assert row["estado"] == "ok"
    assert row["colegios_procesados"] == 42


def test_ultima_ejecucion_ok_devuelve_fecha_si_existe(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    registrar_ejecucion(bd, modulo="descubrir", duracion_segundos=1.0, estado="ok")
    fecha = ultima_ejecucion_ok(bd, modulo="descubrir")
    assert fecha is not None


def test_ultima_ejecucion_ok_devuelve_none_si_no_existe(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    fecha = ultima_ejecucion_ok(bd, modulo="enriquecer")
    assert fecha is None


def test_ultima_ejecucion_ignora_errores(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    registrar_ejecucion(bd, modulo="x", duracion_segundos=1.0, estado="error", mensaje="boom")
    assert ultima_ejecucion_ok(bd, modulo="x") is None
```

- [ ] **Paso 2: Run, see fail**

- [ ] **Paso 3: Agregar a `modulos/db.py`** (al final del archivo):

```python
def registrar_ejecucion(
    ruta_bd,
    *,
    modulo: str,
    duracion_segundos: float,
    estado: str,
    colegios_procesados: int = 0,
    mensaje: str | None = None,
    costo_api_usd: float = 0.0,
) -> None:
    """Inserta una fila en registro_ejecuciones."""
    if estado not in ("ok", "error"):
        raise ValueError(f"estado inválido: {estado}")
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            """INSERT INTO registro_ejecuciones
               (modulo, duracion_segundos, estado, colegios_procesados, mensaje, costo_api_usd)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (modulo, duracion_segundos, estado, colegios_procesados, mensaje, costo_api_usd),
        )
        conn.commit()
    finally:
        conn.close()


def ultima_ejecucion_ok(ruta_bd, modulo: str) -> str | None:
    """Devuelve la fecha (ISO string) de la última ejecución 'ok' del módulo, o None."""
    conn = conectar(ruta_bd)
    try:
        row = conn.execute(
            """SELECT fecha FROM registro_ejecuciones
               WHERE modulo = ? AND estado = 'ok'
               ORDER BY fecha DESC LIMIT 1""",
            (modulo,),
        ).fetchone()
        return row["fecha"] if row else None
    finally:
        conn.close()
```

- [ ] **Paso 4: Run, see pass**

Expected: 4 PASS.

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/db.py tests/test_db_registro.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(db): registrar_ejecucion + ultima_ejecucion_ok"
```

---

## Tarea 11: Orquestador `descubrir`

**Files:**
- Create: `modulos/descubrir.py`
- Test: `tests/test_descubrir.py`

- [ ] **Paso 1: Test (red)**

`tests/test_descubrir.py`:
```python
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from modulos.descubrir import ejecutar
from modulos.db import inicializar_db, contar_colegios
from modulos.scrapers.tipos import ColegioInfo


def _bd_inicializada(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    return bd


def test_descubrir_inserta_colegios_de_men(tmp_path):
    bd = _bd_inicializada(tmp_path)
    csv_men = tmp_path / "men.csv"
    csv_men.write_text(
        "NIT,NOMBRE_ESTABLECIMIENTO,MUNICIPIO,DEPARTAMENTO,NATURALEZA,NIVEL\n"
        "800-1,Colegio Test,BOGOTÁ D.C.,BOGOTÁ D.C.,NO OFICIAL,SECUNDARIA\n",
        encoding="utf-8",
    )

    # Mockear todos los scrapers para que solo MEN devuelva algo
    with patch("modulos.descubrir.scrape_uncoli", return_value=[]), \
         patch("modulos.descubrir.scrape_conaced", return_value=[]), \
         patch("modulos.descubrir.scrape_ascolpem", return_value=[]), \
         patch("modulos.descubrir.queries_a_colegios", return_value=[]):
        ejecutar(ruta_bd=bd, ruta_csv_men=csv_men, queries_path=None,
                 google_api_key=None, google_engine_id=None)

    assert contar_colegios(bd) == 1


def test_descubrir_acumula_fuentes_en_dedup(tmp_path):
    bd = _bd_inicializada(tmp_path)
    csv_men = tmp_path / "men.csv"
    csv_men.write_text(
        "NIT,NOMBRE_ESTABLECIMIENTO,MUNICIPIO,DEPARTAMENTO,NATURALEZA,NIVEL\n"
        "800-1,Colegio Compartido,BOGOTÁ D.C.,BOGOTÁ D.C.,NO OFICIAL,SECUNDARIA\n",
        encoding="utf-8",
    )
    miembro_uncoli = ColegioInfo(
        nombre="Colegio Compartido", ciudad="Bogotá",
        departamento="Bogotá D.C.", fuente="UNCOLI",
    )

    with patch("modulos.descubrir.scrape_uncoli", return_value=[miembro_uncoli]), \
         patch("modulos.descubrir.scrape_conaced", return_value=[]), \
         patch("modulos.descubrir.scrape_ascolpem", return_value=[]), \
         patch("modulos.descubrir.queries_a_colegios", return_value=[]):
        ejecutar(ruta_bd=bd, ruta_csv_men=csv_men, queries_path=None,
                 google_api_key=None, google_engine_id=None)

    assert contar_colegios(bd) == 1  # NO se duplicó
    from modulos.db import conectar
    conn = conectar(bd)
    fuente = conn.execute("SELECT fuente FROM colegios").fetchone()["fuente"]
    conn.close()
    assert "MEN" in fuente
    assert "UNCOLI" in fuente


def test_descubrir_no_falla_si_men_no_existe(tmp_path):
    """Si el CSV del MEN no está, el descubrimiento sigue con las otras fuentes."""
    bd = _bd_inicializada(tmp_path)
    miembro = ColegioInfo(
        nombre="Solo UNCOLI", ciudad="Bogotá",
        departamento="Bogotá D.C.", fuente="UNCOLI",
    )
    with patch("modulos.descubrir.scrape_uncoli", return_value=[miembro]), \
         patch("modulos.descubrir.scrape_conaced", return_value=[]), \
         patch("modulos.descubrir.scrape_ascolpem", return_value=[]), \
         patch("modulos.descubrir.queries_a_colegios", return_value=[]):
        ejecutar(ruta_bd=bd, ruta_csv_men=tmp_path / "no_existe.csv",
                 queries_path=None, google_api_key=None, google_engine_id=None)
    assert contar_colegios(bd) == 1


def test_descubrir_registra_ejecucion(tmp_path):
    bd = _bd_inicializada(tmp_path)
    with patch("modulos.descubrir.scrape_uncoli", return_value=[]), \
         patch("modulos.descubrir.scrape_conaced", return_value=[]), \
         patch("modulos.descubrir.scrape_ascolpem", return_value=[]), \
         patch("modulos.descubrir.queries_a_colegios", return_value=[]):
        ejecutar(ruta_bd=bd, ruta_csv_men=tmp_path / "no.csv",
                 queries_path=None, google_api_key=None, google_engine_id=None)
    from modulos.db import ultima_ejecucion_ok
    assert ultima_ejecucion_ok(bd, modulo="descubrir") is not None
```

- [ ] **Paso 2: Run, see fail**

- [ ] **Paso 3: Implementar `modulos/descubrir.py`**

```python
"""Orquestador del módulo `descubrir`.

Llama a las 5 fuentes (MEN, UNCOLI, CONACED, ASCOLPEM, Google CSE),
inserta en BD con dedup, y registra la ejecución.
"""
import json
import time
from pathlib import Path
from modulos.db import insertar_colegio, registrar_ejecucion
from modulos.logger import obtener_logger
from modulos.scrapers.men import parsear_men
from modulos.scrapers.uncoli import scrape_uncoli
from modulos.scrapers.conaced import scrape_conaced
from modulos.scrapers.ascolpem import scrape_ascolpem
from modulos.scrapers.google_cse import queries_a_colegios
from modulos.scrapers.tipos import ColegioInfo


def _insertar_lote(ruta_bd, lote: list[ColegioInfo], log) -> int:
    """Inserta cada colegio (con dedup automática). Devuelve cuántos NUEVOS se crearon.

    Nota: insertar_colegio devuelve siempre un id; para distinguir nuevo vs existente,
    contamos el total antes y después.
    """
    from modulos.db import contar_colegios
    antes = contar_colegios(ruta_bd)
    procesados_con_error = 0
    for col in lote:
        try:
            insertar_colegio(
                ruta_bd,
                nombre=col.nombre,
                ciudad=col.ciudad,
                departamento=col.departamento,
                fuente=col.fuente,
                nit=col.nit,
                web=col.web,
            )
        except ValueError as e:
            log.warning(f"Saltando colegio inválido: {col.nombre} ({e})")
            procesados_con_error += 1
    nuevos = contar_colegios(ruta_bd) - antes
    if procesados_con_error:
        log.info(f"Lote: {len(lote)} recibidos, {nuevos} nuevos, {procesados_con_error} con error.")
    return nuevos


def ejecutar(
    ruta_bd: Path,
    ruta_csv_men: Path | None = None,
    queries_path: Path | None = None,
    google_api_key: str | None = None,
    google_engine_id: str | None = None,
) -> dict:
    """Corre las 5 fuentes en orden y devuelve un resumen."""
    log = obtener_logger("descubrir")
    inicio = time.monotonic()
    resumen = {"MEN": 0, "UNCOLI": 0, "CONACED": 0, "ASCOLPEM": 0, "Google": 0}
    errores = []

    # 1. MEN
    if ruta_csv_men and Path(ruta_csv_men).exists():
        try:
            log.info(f"Leyendo MEN desde {ruta_csv_men}")
            colegios = parsear_men(ruta_csv_men)
            log.info(f"MEN: {len(colegios)} colegios candidatos")
            resumen["MEN"] = _insertar_lote(ruta_bd, colegios, log)
        except Exception as e:
            log.error(f"MEN falló: {e}")
            errores.append(f"MEN: {e}")
    else:
        log.warning("CSV del MEN no encontrado, se omite esta fuente.")

    # 2. UNCOLI
    try:
        log.info("Scrapeando UNCOLI...")
        resumen["UNCOLI"] = _insertar_lote(ruta_bd, scrape_uncoli(), log)
    except Exception as e:
        log.error(f"UNCOLI falló: {e}")
        errores.append(f"UNCOLI: {e}")

    # 3. CONACED
    try:
        log.info("Scrapeando CONACED...")
        resumen["CONACED"] = _insertar_lote(ruta_bd, scrape_conaced(), log)
    except Exception as e:
        log.error(f"CONACED falló: {e}")
        errores.append(f"CONACED: {e}")

    # 4. ASCOLPEM
    try:
        log.info("Scrapeando ASCOLPEM...")
        resumen["ASCOLPEM"] = _insertar_lote(ruta_bd, scrape_ascolpem(), log)
    except Exception as e:
        log.error(f"ASCOLPEM falló: {e}")
        errores.append(f"ASCOLPEM: {e}")

    # 5. Google CSE
    if queries_path and Path(queries_path).exists() and google_api_key and google_engine_id:
        try:
            log.info(f"Cargando queries de {queries_path}")
            queries = json.loads(Path(queries_path).read_text(encoding="utf-8"))["queries"]
            colegios = queries_a_colegios(queries, google_api_key, google_engine_id)
            log.info(f"Google CSE: {len(colegios)} resultados")
            resumen["Google"] = _insertar_lote(ruta_bd, colegios, log)
        except Exception as e:
            log.error(f"Google CSE falló: {e}")
            errores.append(f"Google: {e}")
    else:
        log.warning("Google CSE no configurado, se omite esta fuente.")

    duracion = time.monotonic() - inicio
    estado = "ok" if not errores else "error"
    mensaje = "; ".join(errores) if errores else None
    total = sum(resumen.values())

    registrar_ejecucion(
        ruta_bd,
        modulo="descubrir",
        duracion_segundos=duracion,
        estado=estado,
        colegios_procesados=total,
        mensaje=mensaje,
    )

    log.info(f"Descubrimiento terminado en {duracion:.1f}s. Resumen: {resumen}")
    return resumen
```

- [ ] **Paso 4: Run, see pass**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pytest.exe C:/Users/elrug/cv-colegios/tests/test_descubrir.py -v
```

Expected: 4 PASS.

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/descubrir.py tests/test_descubrir.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(descubrir): orquestador con 5 fuentes y registro"
```

---

## Tarea 12: CLI `correr_modulo.py`

**Files:**
- Create: `correr_modulo.py` (raíz del proyecto)
- Test: `tests/test_correr_modulo.py`

- [ ] **Paso 1: Test (red)**

`tests/test_correr_modulo.py`:
```python
import sys
from unittest.mock import patch
import pytest
from correr_modulo import main


def test_main_descubrir_invoca_ejecutar(tmp_path, monkeypatch):
    bd = tmp_path / "t.db"
    from modulos.db import inicializar_db
    inicializar_db(bd)

    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=sk-test\nGOOGLE_CSE_API_KEY=k\nGOOGLE_CSE_ENGINE_ID=e\n")

    with patch("correr_modulo.descubrir_ejecutar") as mock_eje:
        mock_eje.return_value = {"MEN": 0, "UNCOLI": 0, "CONACED": 0, "ASCOLPEM": 0, "Google": 0}
        # Simular argv
        monkeypatch.setattr(sys, "argv", ["correr_modulo.py", "descubrir",
                                          "--bd", str(bd), "--env", str(env)])
        main()
    assert mock_eje.called


def test_main_modulo_desconocido_falla(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["correr_modulo.py", "inexistente"])
    with pytest.raises(SystemExit):
        main()
```

- [ ] **Paso 2: Run, see fail**

- [ ] **Paso 3: Implementar `correr_modulo.py`**

```python
"""CLI: corre un módulo del pipeline.

Uso:
    python correr_modulo.py descubrir
    python correr_modulo.py descubrir --bd otra.db --csv-men otro.csv

Por ahora solo soporta 'descubrir'. Otros módulos vendrán en planes posteriores.
"""
import argparse
import sys
from pathlib import Path

from modulos.config import cargar_config, validar_google_cse
from modulos.descubrir import ejecutar as descubrir_ejecutar

RAIZ = Path(__file__).parent
DEFAULT_BD = RAIZ / "data" / "colegios.db"
DEFAULT_ENV = RAIZ / "config" / ".env"
DEFAULT_CSV_MEN = RAIZ / "data" / "raw" / "men_directorio.csv"
DEFAULT_QUERIES = RAIZ / "config" / "queries_google.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI de cv-colegios")
    parser.add_argument("modulo", choices=["descubrir"], help="Módulo a ejecutar")
    parser.add_argument("--bd", default=str(DEFAULT_BD))
    parser.add_argument("--env", default=str(DEFAULT_ENV))
    parser.add_argument("--csv-men", default=str(DEFAULT_CSV_MEN))
    parser.add_argument("--queries", default=str(DEFAULT_QUERIES))
    args = parser.parse_args()

    if args.modulo == "descubrir":
        config = cargar_config(args.env)
        try:
            validar_google_cse(config)
            api_key = config["GOOGLE_CSE_API_KEY"]
            engine_id = config["GOOGLE_CSE_ENGINE_ID"]
        except Exception as e:
            print(f"[!] Google CSE no disponible: {e}")
            print("    Se procederá sin Google CSE; otras fuentes seguirán.")
            api_key = None
            engine_id = None

        resumen = descubrir_ejecutar(
            ruta_bd=Path(args.bd),
            ruta_csv_men=Path(args.csv_men),
            queries_path=Path(args.queries),
            google_api_key=api_key,
            google_engine_id=engine_id,
        )
        total = sum(resumen.values())
        print(f"\nResumen de descubrimiento ({total} colegios nuevos):")
        for fuente, n in resumen.items():
            print(f"  {fuente}: +{n}")
    else:
        print(f"Módulo no soportado todavía: {args.modulo}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Paso 4: Run, see pass**

Expected: 2 PASS. NOTA: el segundo test puede que necesite que `argparse` salga con SystemExit (que es su comportamiento normal cuando recibe choice inválida) — eso está bien.

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add correr_modulo.py tests/test_correr_modulo.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(cli): correr_modulo.py con subcomando descubrir"
```

---

## Tarea 13: Smoke test en vivo (Daniel manual)

Esta tarea la corres tú. Requiere que tengas:
- ✅ El CSV del MEN en `data/raw/men_directorio.csv` (Tarea 4)
- ✅ Google CSE configurado en `config/.env` (Tarea 0)

- [ ] **Paso 1: Resetear la BD para empezar limpio (opcional)**

```powershell
cd C:\Users\elrug\cv-colegios
Remove-Item data\colegios.db.bak.* -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe init_db.py
```

(Esto borra colegios previos si los había. Si quieres conservar la BD anterior, omite este paso — la dedup evitará duplicados.)

- [ ] **Paso 2: Correr descubrimiento**

```powershell
.\.venv\Scripts\python.exe correr_modulo.py descubrir
```

**Lo que vas a ver:**
- Logs en pantalla (también guardados en `data/logs/YYYY-MM-DD.log`).
- Mensajes tipo "Leyendo MEN desde...", "Scrapeando UNCOLI...", etc.
- Al final, un resumen tipo:
  ```
  Resumen de descubrimiento (1247 colegios nuevos):
    MEN: +1100
    UNCOLI: +73
    CONACED: +52
    ASCOLPEM: +18
    Google: +24
  ```
- Tarda probablemente 2-5 minutos (la mayoría es el parseo del CSV del MEN; los scrapers HTTP tardan unos segundos cada uno).

- [ ] **Paso 3: Verificar la BD con DB Browser**

Abre `C:\Users\elrug\cv-colegios\data\colegios.db` con DB Browser for SQLite (https://sqlitebrowser.org/dl/ si no lo tienes).

Verifica:
- ¿Hay >500 filas en la tabla `colegios`? (deberían ser >1000 idealmente).
- Mira algunas filas al azar: ¿los nombres se ven bien? ¿la `fuente` está en formato CSV correcto (ej: `"MEN,UNCOLI"` cuando aplica)?
- En la tabla `registro_ejecuciones` debe haber 1 fila para `modulo='descubrir'` con estado `'ok'`.

- [ ] **Paso 4: Reportar a Claude**

Cuéntame:
- ¿Cuántos colegios totales hay?
- ¿La distribución por fuente es razonable?
- ¿Algo se ve raro (nombres extraños, ciudades incorrectas, departamentos mal escritos)?
- Si hubo errores en pantalla, copia los relevantes.

---

## Verificación final del Plan 2

Cuando termines:

- [ ] CSV del MEN descargado en `data/raw/men_directorio.csv`
- [ ] Google CSE configurado en `config/.env`
- [ ] `pytest tests/ -v` → todos verdes (~80+ tests)
- [ ] `python correr_modulo.py descubrir` corre sin errores fatales
- [ ] BD `data/colegios.db` tiene >500 filas en tabla `colegios`
- [ ] Distribución por fuente razonable (MEN domina, las demás aportan algunas)

Si todo lo anterior se cumple, **Plan 2 está completo**. Avísame y escribo el **Plan 3** (Enriquecimiento — buscar emails y clasificar perfiles pedagógicos).

---

## Notas para el implementador

- **Si UNCOLI/CONACED/ASCOLPEM tienen HTML diferente al fixture:** los selectores CSS en cada scraper fueron diseñados para los fixtures de prueba. Para el smoke test real, cada scraper puede devolver lista vacía si los selectores no matchean. Eso NO es bloqueante: revisar el HTML real de cada sitio en una iteración posterior.
- **Si Google CSE no está configurado:** el orquestador lo salta limpiamente.
- **Si el CSV del MEN tiene columnas con otros nombres:** ajustar `COLUMNAS` en `modulos/scrapers/men.py`.
- **Costos esperados de Plan 2:** $0 USD en API (el descubrimiento no llama a Claude — solo HTTP gratis y Google CSE gratis hasta 100/día).
- **Si después de Tarea 13 hay <100 colegios:** muy probablemente un scraper o el CSV del MEN no está alimentando bien. Es momento de iterar antes de Plan 3.
