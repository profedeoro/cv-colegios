# Plan 3 — Enriquecimiento de colegios

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Para cada colegio en estado `descubierto`, encontrar su sitio web, extraer correo electrónico, clasificar su perfil pedagógico con Claude, y pasarlo a estado `enriquecido` (o `sin_correo` / `error`).

**Architecture:** Pipeline secuencial de 4 etapas dentro de un orquestador con concurrencia limitada (5 simultáneos, max 30 colegios/run). Cada etapa puede fallar individualmente sin tumbar las demás. Brave Search reemplaza a Google CSE para búsquedas web (Google deprecó "Buscar en toda la web").

**Tech Stack:** httpx, selectolax (ya), dnspython (ya), anthropic SDK (ya), **Brave Search API** (nueva).

**Spec referenciado:** `docs/superpowers/specs/2026-05-05-cv-colegios-design.md` — sección 4.2.

---

## Roadmap actualizado

| Plan | Producto al terminar | Estado |
|---|---|---|
| 1. Cimientos + plantilla | Plantilla DOCX pulida + BD | ✅ DONE (33 commits) |
| 2. Descubrimiento | 3.116 colegios en BD desde MEN 2019 + percentil 2021 | ✅ DONE (50 commits) |
| **3. Enriquecimiento (este)** | Colegios con email + perfil pedagógico clasificado | En curso |
| 4. Generación + Envío Gmail | Borradores en Gmail | Próximo |
| 5. Respuestas + Seguimientos | Loop cerrado + notificaciones | Después |
| 6. Orquestación + Despliegue | Pipeline en Programador Windows | Final |

---

## Conceptos clave para Daniel

- **Brave Search API:** Buscador independiente, sin las restricciones de Google CSE. Tier gratis: 1 query/segundo (suficiente para nosotros), hasta 2.000 queries/mes. Para 3.116 colegios distribuidos en varias semanas (~30/día) cabemos cómodamente.
- **MX lookup:** Verifica que el dominio del correo `info@colegio.edu.co` realmente exista (no que le rebote en el primer envío). Usa DNS, gratis.
- **Clasificación pedagógica:** Claude lee 2-3 páginas del sitio del colegio y devuelve un JSON estructurado: `{bilingue: bool, religioso: bool, denominacion: str|null, ib: bool, ...}`. Esto guía la personalización en Plan 4.
- **Concurrencia con asyncio:** En vez de procesar 30 colegios uno tras otro (lento por I/O de red), procesa 5 en paralelo. Reduce el tiempo de ~30 min a ~6 min para una corrida típica.

---

## Estructura de archivos a crear

```
modulos/
├── scrapers/
│   └── brave_search.py         ← cliente Brave Search API (Tarea 2)
├── web_finder.py               ← encontrar_web(nombre, ciudad) (Tarea 3)
├── email_extractor.py          ← extraer + heurística + MX (Tareas 4+5)
├── clasificador_pedagogico.py  ← Claude classifier (Tarea 6)
└── enriquecer.py               ← orquestador (Tarea 7)

prompts/
└── clasificar_colegio.txt      ← prompt de clasificación (Tarea 6)

correr_modulo.py                ← agregar subcomando "enriquecer" (Tarea 8)
```

---

## Tarea 0: Setup de Brave Search API (Daniel manual, ~10 min)

- [ ] **Paso 1: Crear cuenta**

1. Ve a https://api.search.brave.com
2. Click "Sign up" (botón arriba a la derecha).
3. Registra con tu correo `danedu348@gmail.com`. Confirma con el email que te llega.

- [ ] **Paso 2: Suscribirse al plan gratuito**

1. Ve a la sección "API Keys" o "Subscriptions" (varía la UI).
2. Selecciona el plan **"Free AI for plan"** (o "Data for Search" — ambos son gratis y suficientes para nosotros).
3. Si te pide tarjeta de crédito como verificación: pónla. Brave NO te cobra mientras estés en el tier gratis (2.000 queries/mes). Es un anti-fraude estándar.

- [ ] **Paso 3: Generar API key**

1. En "API Keys" → "Generate new key".
2. Nombre: `cv-colegios`.
3. Copia la key generada (es una cadena larga). Guárdala.

- [ ] **Paso 4: Agregar al `.env`**

Abre `C:/Users/elrug/cv-colegios/config/.env` con notepad. Agrega esta línea al final:

```
BRAVE_SEARCH_API_KEY=tu-key-aquí
```

Guarda y cierra. **Avísame cuando esté listo** para que sigan los sub-agentes con las tareas que dependen de Brave (T2, T3, T7+).

---

## Tarea 1: Agregar dependencias + validador opcional Brave en config

**Files:**
- Modify: `requirements.txt` (no cambia, ya tenemos httpx + dnspython)
- Modify: `modulos/config.py` (agregar `validar_brave`)
- Modify: `tests/test_config.py` (3 tests)
- Modify: `config/.env.example` (agregar `BRAVE_SEARCH_API_KEY=`)

- [ ] **Paso 1: Actualizar `.env.example`**

Agregar al final de `C:/Users/elrug/cv-colegios/config/.env.example`:

```
# Brave Search API (Plan 3): https://api.search.brave.com
BRAVE_SEARCH_API_KEY=
```

- [ ] **Paso 2: Test (red)**

Append to `tests/test_config.py`:

```python
def test_validar_brave_falla_si_falta(tmp_path):
    from modulos.config import validar_brave
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-test\n")
    config = cargar_config(env_path=env_file)
    with pytest.raises(ConfigError, match="BRAVE"):
        validar_brave(config)


def test_validar_brave_pasa_si_esta(tmp_path):
    from modulos.config import validar_brave
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=sk-test\n"
        "BRAVE_SEARCH_API_KEY=BSA-test-12345\n"
    )
    config = cargar_config(env_path=env_file)
    validar_brave(config)  # no debe lanzar
```

- [ ] **Paso 3: Run, see fail (ImportError on validar_brave).**

- [ ] **Paso 4: Implementar en `modulos/config.py`** (al final):

```python
def validar_brave(config: dict) -> None:
    """Verifica que la clave de Brave Search esté presente.

    Solo llamar desde módulos que realmente la necesiten (web_finder, enriquecer).
    """
    if not config.get("BRAVE_SEARCH_API_KEY"):
        raise ConfigError(
            "Falta BRAVE_SEARCH_API_KEY. Crea una cuenta en https://api.search.brave.com "
            "y configúrala en config/.env (ver Tarea 0 del plan 3)."
        )
```

- [ ] **Paso 5: Run, see pass (2 new + prior 6 = 8 in test_config).**

- [ ] **Paso 6: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/config.py tests/test_config.py config/.env.example
git -C C:/Users/elrug/cv-colegios commit -m "feat(config): validador para Brave Search API"
```

---

## Tarea 2: Wrapper de Brave Search API

**Files:**
- Create: `modulos/scrapers/brave_search.py`
- Create: `tests/test_brave_search.py`

- [ ] **Paso 1: Test (red)**

`tests/test_brave_search.py`:

```python
import re
import pytest
from modulos.scrapers.brave_search import buscar_brave, BraveError


def test_buscar_brave_devuelve_resultados(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r"https://api\.search\.brave\.com/res/v1/web/search.*"),
        json={
            "web": {
                "results": [
                    {"title": "Colegio X", "url": "https://colegiox.edu.co/", "description": "..."},
                    {"title": "Otro", "url": "https://otro.edu.co/", "description": "..."},
                ]
            }
        },
    )
    resultados = buscar_brave(query="colegio x", api_key="BSA-test")
    assert len(resultados) == 2
    assert resultados[0]["url"] == "https://colegiox.edu.co/"


def test_buscar_brave_envia_token_en_header(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r".*brave.*"),
        json={"web": {"results": []}},
    )
    buscar_brave(query="x", api_key="BSA-secret")
    request = httpx_mock.get_request()
    assert request.headers["X-Subscription-Token"] == "BSA-secret"


def test_buscar_brave_devuelve_vacio_si_sin_resultados(httpx_mock):
    httpx_mock.add_response(url=re.compile(r".*"), json={"web": {"results": []}})
    assert buscar_brave(query="x", api_key="k") == []


def test_buscar_brave_devuelve_vacio_si_no_hay_seccion_web(httpx_mock):
    httpx_mock.add_response(url=re.compile(r".*"), json={"query": {"original": "x"}})
    assert buscar_brave(query="x", api_key="k") == []


def test_buscar_brave_lanza_error_si_status_4xx(httpx_mock):
    httpx_mock.add_response(url=re.compile(r".*"), status_code=401, json={"error": "invalid key"})
    with pytest.raises(BraveError, match="401"):
        buscar_brave(query="x", api_key="k")
```

- [ ] **Paso 2: Run, see fail.**

- [ ] **Paso 3: Implementar `modulos/scrapers/brave_search.py`**

```python
"""Wrapper sobre la API de Brave Search.

Tier gratis: 1 query/segundo, ~2.000 queries/mes.
Docs: https://api.search.brave.com/app/documentation/web-search/get-started
"""
import time
import httpx

URL_API = "https://api.search.brave.com/res/v1/web/search"
RATE_LIMIT_SEGUNDOS = 1.0  # 1 query/segundo en el tier gratis


class BraveError(Exception):
    """Error en la llamada a Brave Search."""


def buscar_brave(query: str, api_key: str, count: int = 10) -> list[dict]:
    """Hace una búsqueda y devuelve la lista de resultados web.

    Cada item es un dict con al menos 'title', 'url', 'description'.
    """
    headers = {
        "X-Subscription-Token": api_key,
        "Accept": "application/json",
    }
    params = {"q": query, "count": count}
    with httpx.Client(headers=headers, timeout=15.0) as cli:
        resp = cli.get(URL_API, params=params)
        if resp.status_code >= 400:
            raise BraveError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
    return data.get("web", {}).get("results", [])
```

- [ ] **Paso 4: Run, see pass (5 tests).**

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/scrapers/brave_search.py tests/test_brave_search.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(brave): wrapper de Brave Search API"
```

---

## Tarea 3: Web finder (encuentra el sitio de un colegio)

**Files:**
- Create: `modulos/web_finder.py`
- Create: `tests/test_web_finder.py`

- [ ] **Paso 1: Test (red)**

`tests/test_web_finder.py`:

```python
from unittest.mock import patch
import pytest
from modulos.web_finder import encontrar_web


def _resultados_mock(urls: list[str]) -> list[dict]:
    return [{"title": f"Colegio {i}", "url": u, "description": ""} for i, u in enumerate(urls)]


def test_encontrar_web_devuelve_primer_edu_co():
    """Prefiere dominios .edu.co sobre otros."""
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = _resultados_mock([
            "https://www.facebook.com/colegio-x",  # ignorar redes sociales
            "https://colegiox.edu.co/",  # este
            "https://otro.edu.co/",
        ])
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert web == "https://colegiox.edu.co/"


def test_encontrar_web_descarta_redes_sociales():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = _resultados_mock([
            "https://www.facebook.com/colegio-x",
            "https://twitter.com/colegio",
            "https://www.linkedin.com/in/colegio",
            "https://www.instagram.com/colegio",
            "https://colegio-x.edu.co/",
        ])
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert "facebook" not in web
    assert "twitter" not in web
    assert ".edu.co" in web


def test_encontrar_web_acepta_otros_tld_si_no_hay_edu_co():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = _resultados_mock([
            "https://www.colegio-x.com/",
            "https://www.colegio-x.org/",
        ])
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert web == "https://www.colegio-x.com/"  # primer no-red-social


def test_encontrar_web_devuelve_none_sin_resultados():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = []
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert web is None


def test_encontrar_web_devuelve_none_si_solo_redes_sociales():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = _resultados_mock([
            "https://www.facebook.com/x",
            "https://twitter.com/x",
        ])
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert web is None


def test_encontrar_web_arma_query_correcta():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = []
        encontrar_web("Colegio San Tarsicio", "Bogotá", api_key="BSA-test")
        args, kwargs = mock.call_args
        query = kwargs.get("query") or args[0]
        assert "Colegio San Tarsicio" in query
        assert "Bogotá" in query
```

- [ ] **Paso 2: Run, see fail.**

- [ ] **Paso 3: Implementar `modulos/web_finder.py`**

```python
"""Encuentra el sitio web oficial de un colegio usando Brave Search.

Heurística: descarta redes sociales y directorios, prefiere .edu.co.
"""
from urllib.parse import urlparse
from modulos.scrapers.brave_search import buscar_brave

# Dominios a ignorar (redes sociales, directorios genéricos, agregadores).
DOMINIOS_BLACKLIST = {
    "facebook.com", "www.facebook.com", "fb.com",
    "twitter.com", "www.twitter.com", "x.com", "www.x.com",
    "instagram.com", "www.instagram.com",
    "linkedin.com", "www.linkedin.com",
    "youtube.com", "www.youtube.com", "youtu.be",
    "tiktok.com", "www.tiktok.com",
    "wikipedia.org", "es.wikipedia.org",
    "google.com", "www.google.com",
    "datos.gov.co", "www.datos.gov.co",
    "mineducacion.gov.co", "www.mineducacion.gov.co",
    "icfes.gov.co", "www.icfes.gov.co",
}


def _es_aceptable(url: str) -> bool:
    """True si la URL no es de un dominio blacklisted."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    if not host:
        return False
    return host not in DOMINIOS_BLACKLIST


def _es_edu_co(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return host.endswith(".edu.co")


def encontrar_web(nombre_colegio: str, ciudad: str, api_key: str) -> str | None:
    """Busca el sitio web del colegio en Brave. Devuelve URL o None."""
    query = f"{nombre_colegio} {ciudad} colegio sitio oficial"
    resultados = buscar_brave(query=query, api_key=api_key, count=10)
    aceptables = [r["url"] for r in resultados if _es_aceptable(r.get("url", ""))]
    if not aceptables:
        return None
    # Preferencia: primero un .edu.co, si no, el primero aceptable.
    edu_co = [u for u in aceptables if _es_edu_co(u)]
    return edu_co[0] if edu_co else aceptables[0]
```

- [ ] **Paso 4: Run, see pass (6 tests).**

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/web_finder.py tests/test_web_finder.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(web): encontrar sitio web del colegio con Brave + heurística"
```

---

## Tarea 4: Email extractor + heurística + MX validation

**Files:**
- Create: `modulos/email_extractor.py`
- Create: `tests/test_email_extractor.py`

- [ ] **Paso 1: Test (red)**

`tests/test_email_extractor.py`:

```python
from unittest.mock import patch
import pytest
from modulos.email_extractor import (
    extraer_emails,
    seleccionar_destinatario,
    validar_dominio,
)


def test_extraer_emails_simple():
    html = "<html>contacto@colegio.edu.co y rector@colegio.edu.co</html>"
    emails = extraer_emails(html)
    assert "contacto@colegio.edu.co" in emails
    assert "rector@colegio.edu.co" in emails


def test_extraer_emails_quita_duplicados():
    html = "info@x.co info@x.co INFO@x.co"
    emails = extraer_emails(html)
    # Normaliza a lowercase, conserva uno
    assert emails.count("info@x.co") == 1


def test_extraer_emails_descarta_basura():
    html = "abc@def, foo@bar.x, valido@col.edu.co"
    emails = extraer_emails(html)
    # Solo emails con TLD razonable
    assert "valido@col.edu.co" in emails
    assert "abc@def" not in emails


def test_seleccionar_prefiere_rector():
    emails = ["info@x.co", "rector@x.co", "contacto@x.co"]
    assert seleccionar_destinatario(emails) == "rector@x.co"


def test_seleccionar_prefiere_direccion_si_no_rector():
    emails = ["info@x.co", "direccion@x.co", "contacto@x.co"]
    assert seleccionar_destinatario(emails) == "direccion@x.co"


def test_seleccionar_jerarquia_completa():
    """rector > direccion > recursos.humanos > talento > info > contacto > shortest."""
    pares = [
        (["talento@x.co", "info@x.co"], "talento@x.co"),
        (["info@x.co", "contacto@x.co"], "info@x.co"),
        (["recursos.humanos@x.co", "info@x.co"], "recursos.humanos@x.co"),
    ]
    for emails, esperado in pares:
        assert seleccionar_destinatario(emails) == esperado


def test_seleccionar_devuelve_none_lista_vacia():
    assert seleccionar_destinatario([]) is None


def test_seleccionar_fallback_al_mas_corto_si_ninguno_encaja():
    emails = ["administracion@x.co", "abc@x.co"]
    # Ninguno encaja en jerarquía → el más corto
    assert seleccionar_destinatario(emails) == "abc@x.co"


def test_validar_dominio_acepta_dominio_valido():
    """Dominio real con MX (e.g., gmail.com)."""
    # Test con un dominio que sabemos tiene MX
    assert validar_dominio("test@gmail.com") is True


def test_validar_dominio_rechaza_dominio_inexistente():
    """Dominio que NO tiene MX records (sintético)."""
    # Usar un dominio claramente inexistente
    assert validar_dominio("test@este-dominio-no-existe-12345xyz.tld") is False


def test_validar_dominio_rechaza_email_malformado():
    assert validar_dominio("notanemail") is False
    assert validar_dominio("@x.co") is False
    assert validar_dominio("x@") is False
```

- [ ] **Paso 2: Run, see fail.**

- [ ] **Paso 3: Implementar `modulos/email_extractor.py`**

```python
"""Extracción de emails, selección de destinatario, validación MX."""
import re
import dns.resolver
import dns.exception

# Regex moderado: requiere TLD de al menos 2 letras (no captura "abc@def")
RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Prefijos en orden de preferencia (más arriba = más relevante para Daniel).
PREFIJOS_PREFERIDOS = [
    "rector",
    "direccion", "dirección",
    "recursos.humanos", "rrhh", "talento.humano",
    "talento",
    "secretaria.academica",
    "info", "informacion", "información",
    "contacto",
]


def extraer_emails(html: str) -> list[str]:
    """Extrae emails únicos (case-insensitive) del HTML."""
    encontrados = RE_EMAIL.findall(html)
    # Normalizar a lowercase y deduplicar preservando orden de aparición
    vistos = set()
    resultado = []
    for e in encontrados:
        e_low = e.lower()
        if e_low not in vistos:
            vistos.add(e_low)
            resultado.append(e_low)
    return resultado


def seleccionar_destinatario(emails: list[str]) -> str | None:
    """Aplica heurística de preferencia. Devuelve el mejor email o None."""
    if not emails:
        return None
    # Buscar por prefijo en orden de preferencia
    for prefijo in PREFIJOS_PREFERIDOS:
        for e in emails:
            local = e.split("@")[0]
            if local.lower() == prefijo:
                return e
    # Ninguno encaja → el más corto (suele ser el más institucional)
    return min(emails, key=len)


def validar_dominio(email: str) -> bool:
    """True si el dominio del email tiene registros MX (DNS lookup)."""
    if "@" not in email:
        return False
    parts = email.split("@", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False
    dominio = parts[1]
    try:
        respuesta = dns.resolver.resolve(dominio, "MX", lifetime=5.0)
        return len(respuesta) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
            dns.resolver.NoNameservers, dns.exception.Timeout):
        return False
```

- [ ] **Paso 4: Run, see pass (11 tests). NOTA: el test `test_validar_dominio_acepta_dominio_valido` requiere conexión a internet (DNS lookup real a gmail.com). Si no hay internet, el test se salta o falla — eso es esperado.**

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/email_extractor.py tests/test_email_extractor.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(email): extracción + heurística + MX validation"
```

---

## Tarea 5: Prompt + clasificador pedagógico

**Files:**
- Create: `prompts/clasificar_colegio.txt`
- Create: `modulos/clasificador_pedagogico.py`
- Create: `tests/test_clasificador.py`

- [ ] **Paso 1: Crear el prompt**

`prompts/clasificar_colegio.txt`:

```
Eres un analista experto en educación colombiana.

Recibirás el texto extraído del sitio web de un colegio privado. Tu tarea: identificar su perfil pedagógico y devolver un JSON estricto.

NO inventes información. Si no encuentras evidencia clara de algún campo, déjalo en el valor por defecto (false / null / "desconocido").

Devuelve EXACTAMENTE este JSON, sin nada antes ni después:

```json
{
  "bilingue": false,
  "idioma_segundo": null,
  "religioso": false,
  "denominacion": null,
  "ib": false,
  "montessori": false,
  "enfoque_deportivo": false,
  "enfoque_tecnico": false,
  "enfasis_tic": false,
  "tamano_estimado": "desconocido",
  "palabras_clave": []
}
```

Reglas:
- `bilingue`: true SOLO si el sitio menciona explícitamente "bilingüe", "bilingual", "english program", "inmersión en inglés" o similar.
- `idioma_segundo`: si bilingue=true, el idioma ("inglés", "francés", "alemán", etc.). Si no, null.
- `religioso`: true si menciona alguna confesión religiosa específica (católico, cristiano, evangélico, etc.).
- `denominacion`: si religioso=true, el nombre de la orden o denominación específica si aparece (ej: "calasanz", "lasallista", "jesuita", "salesiano", "carmelitas", "dominicas"). Si religioso pero sin denominación específica, "general". Si no religioso, null.
- `ib`: true si menciona "Bachillerato Internacional" o "International Baccalaureate" o "IB".
- `montessori`: true si menciona "Montessori" en su modelo pedagógico (no solo como referencia).
- `enfoque_deportivo`: true si tiene énfasis en deporte (selecciones, instalaciones deportivas destacadas, etc.).
- `enfoque_tecnico`: true si es técnico, técnico-comercial, agropecuario, industrial, etc.
- `enfasis_tic`: true si menciona "innovación digital", "STEM", "robótica", "programación", "tecnologías".
- `tamano_estimado`: "pequeño" (<300 estudiantes), "mediano" (300-1000), "grande" (>1000), o "desconocido".
- `palabras_clave`: lista de 5-10 términos distintivos que aparecen frecuentemente en el sitio. Ejemplos: ["valores cristianos", "innovación", "STEM", "IB", "campestre", "comunidad"].

NO modifiques los nombres de las claves. Devuelve UN solo objeto JSON.
```

- [ ] **Paso 2: Test (red)**

`tests/test_clasificador.py`:

```python
import json
from unittest.mock import MagicMock, patch
from modulos.clasificador_pedagogico import clasificar


def _mock_claude(respuesta: str):
    cliente = MagicMock()
    cliente.preguntar.return_value = (respuesta, 0.001)
    return cliente


def test_clasificar_devuelve_dict_con_campos_esperados():
    respuesta = json.dumps({
        "bilingue": True,
        "idioma_segundo": "inglés",
        "religioso": False,
        "denominacion": None,
        "ib": True,
        "montessori": False,
        "enfoque_deportivo": False,
        "enfoque_tecnico": False,
        "enfasis_tic": True,
        "tamano_estimado": "grande",
        "palabras_clave": ["bilingüe", "IB", "innovación"],
    })
    cliente = _mock_claude(respuesta)
    perfil, costo = clasificar("texto del sitio web", cliente)
    assert perfil["bilingue"] is True
    assert perfil["idioma_segundo"] == "inglés"
    assert perfil["ib"] is True
    assert costo == 0.001


def test_clasificar_acepta_respuesta_con_code_fence():
    respuesta = "```json\n" + json.dumps({"bilingue": False, "religioso": False, "denominacion": None,
                                           "idioma_segundo": None, "ib": False, "montessori": False,
                                           "enfoque_deportivo": False, "enfoque_tecnico": False,
                                           "enfasis_tic": False, "tamano_estimado": "desconocido",
                                           "palabras_clave": []}) + "\n```"
    cliente = _mock_claude(respuesta)
    perfil, _ = clasificar("texto", cliente)
    assert perfil["bilingue"] is False


def test_clasificar_lanza_si_json_malformado():
    cliente = _mock_claude("esto no es json")
    import pytest
    with pytest.raises(ValueError):
        clasificar("texto", cliente)
```

- [ ] **Paso 3: Run, see fail.**

- [ ] **Paso 4: Implementar `modulos/clasificador_pedagogico.py`**

```python
"""Clasificador de perfil pedagógico usando Claude."""
import json
from pathlib import Path

RUTA_PROMPT = Path(__file__).parent.parent / "prompts" / "clasificar_colegio.txt"
MAX_TOKENS = 1500
MAX_CHARS_INPUT = 10000  # límite para no inflar tokens


def _parsear_json(respuesta: str) -> dict:
    """Parsea JSON tolerante a code fences."""
    raw = respuesta.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.lower().lstrip().startswith("json"):
            if "\n" in raw:
                raw = raw[raw.index("\n") + 1:]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw.strip())


def clasificar(texto_sitio: str, cliente_claude) -> tuple[dict, float]:
    """Pide a Claude clasificar el perfil pedagógico. Devuelve (perfil, costo_usd)."""
    sistema = RUTA_PROMPT.read_text(encoding="utf-8")
    usuario = texto_sitio[:MAX_CHARS_INPUT]
    respuesta, costo = cliente_claude.preguntar(
        sistema=sistema,
        usuario=usuario,
        max_tokens=MAX_TOKENS,
        cachear_sistema=True,
    )
    perfil = _parsear_json(respuesta)
    return perfil, costo
```

- [ ] **Paso 5: Run, see pass (3 tests).**

- [ ] **Paso 6: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add prompts/clasificar_colegio.txt modulos/clasificador_pedagogico.py tests/test_clasificador.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(clasificador): perfil pedagógico con Claude (prompt + cliente)"
```

---

## Tarea 6: Helpers de BD para enriquecimiento

**Files:**
- Modify: `modulos/db.py` (agregar 3 funciones)
- Create: `tests/test_db_enriquecer.py`

- [ ] **Paso 1: Test (red)**

`tests/test_db_enriquecer.py`:

```python
import json
from modulos.db import (
    inicializar_db, insertar_colegio,
    colegios_para_enriquecer, marcar_enriquecido, marcar_sin_correo, incrementar_intento_enriquecer,
    conectar,
)


def _bd_con_colegios(tmp_path, n=5):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    for i in range(n):
        insertar_colegio(bd, nombre=f"Colegio Test {i}", ciudad="Bogotá",
                         departamento="Bogotá D.C.", fuente="MEN")
    return bd


def test_colegios_para_enriquecer_devuelve_solo_descubiertos(tmp_path):
    bd = _bd_con_colegios(tmp_path, n=5)
    pendientes = colegios_para_enriquecer(bd, limite=10)
    assert len(pendientes) == 5
    assert all(c["estado"] == "descubierto" for c in pendientes)


def test_colegios_para_enriquecer_respeta_limite(tmp_path):
    bd = _bd_con_colegios(tmp_path, n=10)
    pendientes = colegios_para_enriquecer(bd, limite=3)
    assert len(pendientes) == 3


def test_colegios_para_enriquecer_excluye_con_3_intentos(tmp_path):
    bd = _bd_con_colegios(tmp_path, n=2)
    cid = colegios_para_enriquecer(bd, limite=10)[0]["id"]
    incrementar_intento_enriquecer(bd, cid)
    incrementar_intento_enriquecer(bd, cid)
    incrementar_intento_enriquecer(bd, cid)
    pendientes = colegios_para_enriquecer(bd, limite=10)
    ids = [c["id"] for c in pendientes]
    assert cid not in ids


def test_marcar_enriquecido_actualiza_campos(tmp_path):
    bd = _bd_con_colegios(tmp_path, n=1)
    cid = colegios_para_enriquecer(bd, limite=1)[0]["id"]
    marcar_enriquecido(bd, cid,
                       web="https://x.edu.co",
                       correo="info@x.edu.co",
                       correo_destinatario="rector@x.edu.co",
                       perfil_pedagogico={"bilingue": True},
                       palabras_clave=["IB", "innovación"])
    conn = conectar(bd)
    row = conn.execute("SELECT * FROM colegios WHERE id = ?", (cid,)).fetchone()
    conn.close()
    assert row["estado"] == "enriquecido"
    assert row["web"] == "https://x.edu.co"
    assert row["correo"] == "info@x.edu.co"
    assert row["correo_destinatario"] == "rector@x.edu.co"
    assert json.loads(row["perfil_pedagogico"])["bilingue"] is True
    assert json.loads(row["palabras_clave"]) == ["IB", "innovación"]
    assert row["fecha_enriquecido"] is not None


def test_marcar_sin_correo_cambia_estado(tmp_path):
    bd = _bd_con_colegios(tmp_path, n=1)
    cid = colegios_para_enriquecer(bd, limite=1)[0]["id"]
    marcar_sin_correo(bd, cid, web="https://x.edu.co")
    conn = conectar(bd)
    row = conn.execute("SELECT estado, web FROM colegios WHERE id = ?", (cid,)).fetchone()
    conn.close()
    assert row["estado"] == "sin_correo"
    assert row["web"] == "https://x.edu.co"
```

- [ ] **Paso 2: Run, see fail.**

- [ ] **Paso 3: Agregar a `modulos/db.py` (al final):**

```python
import json as _json


def colegios_para_enriquecer(ruta_bd, limite: int = 30) -> list[dict]:
    """Devuelve colegios en estado 'descubierto' con < 3 intentos, ordenados por fecha_descubierto."""
    conn = conectar(ruta_bd)
    try:
        rows = conn.execute(
            """SELECT * FROM colegios
               WHERE estado = 'descubierto' AND intentos_enriquecer < 3
               ORDER BY fecha_descubierto ASC
               LIMIT ?""",
            (limite,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def marcar_enriquecido(
    ruta_bd, colegio_id: int,
    *, web: str | None, correo: str | None, correo_destinatario: str | None,
    perfil_pedagogico: dict, palabras_clave: list[str],
) -> None:
    """Marca un colegio como enriquecido y actualiza sus datos."""
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            """UPDATE colegios SET
                 estado = 'enriquecido',
                 web = COALESCE(web, ?),
                 correo = ?,
                 correo_destinatario = ?,
                 perfil_pedagogico = ?,
                 palabras_clave = ?,
                 fecha_enriquecido = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (web, correo, correo_destinatario,
             _json.dumps(perfil_pedagogico, ensure_ascii=False),
             _json.dumps(palabras_clave, ensure_ascii=False),
             colegio_id),
        )
        conn.commit()
    finally:
        conn.close()


def marcar_sin_correo(ruta_bd, colegio_id: int, *, web: str | None = None) -> None:
    """Marca un colegio como sin_correo (web encontrada pero no email válido)."""
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            """UPDATE colegios SET estado = 'sin_correo',
                                    web = COALESCE(web, ?),
                                    fecha_enriquecido = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (web, colegio_id),
        )
        conn.commit()
    finally:
        conn.close()


def incrementar_intento_enriquecer(ruta_bd, colegio_id: int) -> None:
    """Incrementa contador de intentos. Si llega a 3, el colegio queda fuera del próximo lote."""
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            "UPDATE colegios SET intentos_enriquecer = intentos_enriquecer + 1 WHERE id = ?",
            (colegio_id,),
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Paso 4: Run, see pass (5 tests).**

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/db.py tests/test_db_enriquecer.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(db): helpers para módulo enriquecer (selección + transiciones)"
```

---

## Tarea 7: Orquestador `enriquecer`

**Files:**
- Create: `modulos/enriquecer.py`
- Create: `tests/test_enriquecer.py`

- [ ] **Paso 1: Test (red)**

`tests/test_enriquecer.py`:

```python
from unittest.mock import patch, MagicMock
import pytest
from modulos.enriquecer import procesar_colegio
from modulos.db import inicializar_db, insertar_colegio, conectar


def _bd_con_colegio(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    cid = insertar_colegio(bd, nombre="Colegio Test", ciudad="Bogotá",
                            departamento="Bogotá D.C.", fuente="MEN")
    return bd, cid


def test_procesar_colegio_marca_enriquecido_si_todo_ok(tmp_path):
    bd, cid = _bd_con_colegio(tmp_path)
    colegio = {"id": cid, "nombre": "Colegio Test", "ciudad": "Bogotá",
               "departamento": "Bogotá D.C.", "web": None}

    cliente_claude = MagicMock()
    cliente_claude.preguntar.return_value = (
        '{"bilingue": true, "idioma_segundo": "inglés", "religioso": false,'
        ' "denominacion": null, "ib": false, "montessori": false,'
        ' "enfoque_deportivo": false, "enfoque_tecnico": false, "enfasis_tic": true,'
        ' "tamano_estimado": "mediano", "palabras_clave": ["bilingüe", "innovación"]}',
        0.01,
    )

    with patch("modulos.enriquecer.encontrar_web", return_value="https://test.edu.co/"), \
         patch("modulos.enriquecer.fetch_html", return_value="<html>info@test.edu.co rector@test.edu.co</html>"), \
         patch("modulos.enriquecer.validar_dominio", return_value=True):
        resultado = procesar_colegio(bd, colegio, cliente_claude, brave_api_key="BSA-test")

    assert resultado["estado_final"] == "enriquecido"
    conn = conectar(bd)
    row = conn.execute("SELECT estado, web, correo_destinatario FROM colegios WHERE id = ?", (cid,)).fetchone()
    conn.close()
    assert row["estado"] == "enriquecido"
    assert row["web"] == "https://test.edu.co/"
    assert row["correo_destinatario"] == "rector@test.edu.co"


def test_procesar_colegio_sin_web_marca_sin_correo(tmp_path):
    bd, cid = _bd_con_colegio(tmp_path)
    colegio = {"id": cid, "nombre": "Colegio Test", "ciudad": "Bogotá",
               "departamento": "Bogotá D.C.", "web": None}
    cliente_claude = MagicMock()

    with patch("modulos.enriquecer.encontrar_web", return_value=None):
        resultado = procesar_colegio(bd, colegio, cliente_claude, brave_api_key="BSA-test")

    assert resultado["estado_final"] == "sin_correo"
    conn = conectar(bd)
    estado = conn.execute("SELECT estado FROM colegios WHERE id = ?", (cid,)).fetchone()["estado"]
    conn.close()
    assert estado == "sin_correo"


def test_procesar_colegio_sin_email_valido_marca_sin_correo(tmp_path):
    bd, cid = _bd_con_colegio(tmp_path)
    colegio = {"id": cid, "nombre": "Colegio Test", "ciudad": "Bogotá",
               "departamento": "Bogotá D.C.", "web": None}
    cliente_claude = MagicMock()

    with patch("modulos.enriquecer.encontrar_web", return_value="https://x.edu.co/"), \
         patch("modulos.enriquecer.fetch_html", return_value="<html>sin emails aqui</html>"):
        resultado = procesar_colegio(bd, colegio, cliente_claude, brave_api_key="BSA-test")

    assert resultado["estado_final"] == "sin_correo"


def test_procesar_colegio_email_dominio_invalido_marca_sin_correo(tmp_path):
    bd, cid = _bd_con_colegio(tmp_path)
    colegio = {"id": cid, "nombre": "Colegio Test", "ciudad": "Bogotá",
               "departamento": "Bogotá D.C.", "web": None}
    cliente_claude = MagicMock()

    with patch("modulos.enriquecer.encontrar_web", return_value="https://x.edu.co/"), \
         patch("modulos.enriquecer.fetch_html", return_value="<html>info@dominio-falso-12345.tld</html>"), \
         patch("modulos.enriquecer.validar_dominio", return_value=False):
        resultado = procesar_colegio(bd, colegio, cliente_claude, brave_api_key="BSA-test")

    assert resultado["estado_final"] == "sin_correo"


def test_procesar_colegio_falla_fetch_incrementa_intento(tmp_path):
    bd, cid = _bd_con_colegio(tmp_path)
    colegio = {"id": cid, "nombre": "Colegio Test", "ciudad": "Bogotá",
               "departamento": "Bogotá D.C.", "web": None}
    cliente_claude = MagicMock()

    from modulos.http_cliente import HttpError
    with patch("modulos.enriquecer.encontrar_web", return_value="https://x.edu.co/"), \
         patch("modulos.enriquecer.fetch_html", side_effect=HttpError("timeout")):
        resultado = procesar_colegio(bd, colegio, cliente_claude, brave_api_key="BSA-test")

    assert resultado["estado_final"] == "error"
    conn = conectar(bd)
    intentos = conn.execute("SELECT intentos_enriquecer FROM colegios WHERE id = ?", (cid,)).fetchone()[0]
    conn.close()
    assert intentos == 1
```

- [ ] **Paso 2: Run, see fail.**

- [ ] **Paso 3: Implementar `modulos/enriquecer.py`**

```python
"""Orquestador del módulo enriquecer.

Para cada colegio en estado 'descubierto':
1. Encontrar su web (si no la tiene) usando Brave Search.
2. Bajar el HTML de la home.
3. Extraer emails y elegir destinatario por heurística.
4. Validar dominio del correo (MX lookup).
5. Clasificar perfil pedagógico con Claude.
6. Marcar como 'enriquecido' o 'sin_correo' o 'error' según resultado.
"""
import time
from pathlib import Path
from selectolax.parser import HTMLParser

from modulos.db import (
    colegios_para_enriquecer,
    marcar_enriquecido,
    marcar_sin_correo,
    incrementar_intento_enriquecer,
    registrar_ejecucion,
)
from modulos.email_extractor import extraer_emails, seleccionar_destinatario, validar_dominio
from modulos.http_cliente import fetch_html, HttpError
from modulos.logger import obtener_logger
from modulos.web_finder import encontrar_web
from modulos.clasificador_pedagogico import clasificar


def _texto_visible(html: str) -> str:
    """Extrae texto visible del HTML (sin tags, scripts, estilos). Limita a 10000 chars."""
    tree = HTMLParser(html)
    for nodo in tree.css("script, style, noscript"):
        nodo.decompose()
    texto = tree.body.text(separator=" ", strip=True) if tree.body else ""
    return texto[:10000]


def procesar_colegio(ruta_bd, colegio: dict, cliente_claude, brave_api_key: str) -> dict:
    """Procesa un colegio completo. Devuelve dict con resumen del resultado."""
    log = obtener_logger("enriquecer")
    cid = colegio["id"]
    nombre = colegio["nombre"]
    web_existente = colegio.get("web")

    # 1. Encontrar web (si no la tiene)
    web = web_existente
    if not web:
        try:
            web = encontrar_web(nombre, colegio["ciudad"], api_key=brave_api_key)
        except Exception as e:
            log.warning(f"[{cid}] Error buscando web de '{nombre}': {e}")
            web = None

    if not web:
        log.info(f"[{cid}] Sin web encontrada para '{nombre}'")
        marcar_sin_correo(ruta_bd, cid, web=None)
        return {"colegio_id": cid, "estado_final": "sin_correo", "razon": "no_web"}

    # 2. Descargar HTML de la home
    try:
        html = fetch_html(web)
    except HttpError as e:
        log.warning(f"[{cid}] Falló descarga de {web}: {e}")
        incrementar_intento_enriquecer(ruta_bd, cid)
        return {"colegio_id": cid, "estado_final": "error", "razon": str(e)}

    # 3. Extraer emails y elegir destinatario
    emails = extraer_emails(html)
    destinatario = seleccionar_destinatario(emails)
    if not destinatario:
        log.info(f"[{cid}] Web encontrada ({web}) pero sin emails")
        marcar_sin_correo(ruta_bd, cid, web=web)
        return {"colegio_id": cid, "estado_final": "sin_correo", "razon": "sin_email"}

    # 4. Validar dominio
    if not validar_dominio(destinatario):
        log.info(f"[{cid}] Email {destinatario} con dominio inválido")
        marcar_sin_correo(ruta_bd, cid, web=web)
        return {"colegio_id": cid, "estado_final": "sin_correo", "razon": "dominio_invalido"}

    # 5. Clasificar perfil pedagógico
    texto = _texto_visible(html)
    try:
        perfil, costo = clasificar(texto, cliente_claude)
    except (ValueError, KeyError) as e:
        log.warning(f"[{cid}] Clasificación falló: {e}")
        incrementar_intento_enriquecer(ruta_bd, cid)
        return {"colegio_id": cid, "estado_final": "error", "razon": f"clasificacion: {e}"}

    palabras_clave = perfil.pop("palabras_clave", [])
    marcar_enriquecido(
        ruta_bd, cid,
        web=web,
        correo=emails[0] if emails else None,
        correo_destinatario=destinatario,
        perfil_pedagogico=perfil,
        palabras_clave=palabras_clave,
    )
    log.info(f"[{cid}] Enriquecido: {nombre} ({destinatario})")
    return {"colegio_id": cid, "estado_final": "enriquecido", "costo": costo}


def ejecutar(
    ruta_bd: Path,
    cliente_claude,
    brave_api_key: str,
    max_colegios: int = 30,
) -> dict:
    """Procesa hasta max_colegios pendientes y devuelve resumen."""
    log = obtener_logger("enriquecer")
    log.info(f"Iniciando enriquecimiento (max={max_colegios})")
    inicio = time.monotonic()

    pendientes = colegios_para_enriquecer(ruta_bd, limite=max_colegios)
    log.info(f"Pendientes encontrados: {len(pendientes)}")

    resumen = {"enriquecido": 0, "sin_correo": 0, "error": 0}
    costo_total = 0.0
    for col in pendientes:
        resultado = procesar_colegio(ruta_bd, col, cliente_claude, brave_api_key)
        resumen[resultado["estado_final"]] = resumen.get(resultado["estado_final"], 0) + 1
        costo_total += resultado.get("costo", 0)

    duracion = time.monotonic() - inicio
    estado = "ok" if resumen["error"] < len(pendientes) else "error"
    registrar_ejecucion(
        ruta_bd, modulo="enriquecer", duracion_segundos=duracion,
        estado=estado, colegios_procesados=len(pendientes),
        costo_api_usd=costo_total,
    )
    log.info(f"Enriquecimiento terminado en {duracion:.1f}s. Resumen: {resumen}. Costo: ${costo_total:.4f}")
    return {"resumen": resumen, "costo_usd": costo_total, "duracion_seg": duracion}
```

- [ ] **Paso 4: Run, see pass (5 tests).**

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add modulos/enriquecer.py tests/test_enriquecer.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(enriquecer): orquestador con web finder + email + clasificación"
```

---

## Tarea 8: CLI integration

**Files:**
- Modify: `correr_modulo.py`
- Modify: `tests/test_correr_modulo.py`

- [ ] **Paso 1: Test (red)**

Append to `tests/test_correr_modulo.py`:

```python
def test_main_enriquecer_invoca_ejecutar(tmp_path, monkeypatch):
    bd = tmp_path / "t.db"
    from modulos.db import inicializar_db
    inicializar_db(bd)
    env = tmp_path / ".env"
    env.write_text(
        "ANTHROPIC_API_KEY=sk-test\n"
        "BRAVE_SEARCH_API_KEY=BSA-test\n"
    )
    with patch("correr_modulo.enriquecer_ejecutar") as mock_eje:
        mock_eje.return_value = {"resumen": {"enriquecido": 5, "sin_correo": 2, "error": 0},
                                 "costo_usd": 0.5, "duracion_seg": 30}
        monkeypatch.setattr(sys, "argv", ["correr_modulo.py", "enriquecer",
                                          "--bd", str(bd), "--env", str(env), "--max", "10"])
        main()
    assert mock_eje.called
```

- [ ] **Paso 2: Run, see fail (modulo no es 'enriquecer' en choices).**

- [ ] **Paso 3: Modificar `correr_modulo.py`**

Cambiar la línea de `argparse`:
```python
parser.add_argument("modulo", choices=["descubrir"], help="Módulo a ejecutar")
```
a:
```python
parser.add_argument("modulo", choices=["descubrir", "enriquecer"], help="Módulo a ejecutar")
parser.add_argument("--max", type=int, default=30, help="Máximo de colegios a procesar (solo enriquecer)")
```

Agregar al inicio del archivo:
```python
from modulos.cliente_claude import ClienteClaude
from modulos.enriquecer import ejecutar as enriquecer_ejecutar
from modulos.config import validar_brave
```

Agregar el bloque del nuevo subcomando dentro de `main()`, después del bloque `if args.modulo == "descubrir":`:

```python
    elif args.modulo == "enriquecer":
        config = cargar_config(args.env)
        validar_brave(config)
        cliente = ClienteClaude(api_key=config["ANTHROPIC_API_KEY"])
        resultado = enriquecer_ejecutar(
            ruta_bd=Path(args.bd),
            cliente_claude=cliente,
            brave_api_key=config["BRAVE_SEARCH_API_KEY"],
            max_colegios=args.max,
        )
        r = resultado["resumen"]
        print(f"\nResumen de enriquecimiento:")
        print(f"  Enriquecidos: +{r.get('enriquecido', 0)}")
        print(f"  Sin correo:   +{r.get('sin_correo', 0)}")
        print(f"  Errores:      +{r.get('error', 0)}")
        print(f"  Costo: ${resultado['costo_usd']:.4f} USD")
        print(f"  Duración: {resultado['duracion_seg']:.1f} seg")
```

- [ ] **Paso 4: Run, see pass.**

- [ ] **Paso 5: Commit**

```bash
git -C C:/Users/elrug/cv-colegios add correr_modulo.py tests/test_correr_modulo.py
git -C C:/Users/elrug/cv-colegios commit -m "feat(cli): subcomando enriquecer"
```

---

## Tarea 9: Smoke test (Daniel manual, ~5 min)

Pre-requisito: Tarea 0 completada (Brave API key en `.env`).

- [ ] **Paso 1: Correr enriquecimiento de 5 colegios para validar**

```powershell
cd C:\Users\elrug\cv-colegios
.\.venv\Scripts\python.exe correr_modulo.py enriquecer --max 5
```

Esto procesa solo 5 colegios. Tarda ~3-5 minutos (descarga webs + llama Claude).

**Resultado esperado:**
```
Resumen de enriquecimiento:
  Enriquecidos: +3
  Sin correo:   +1
  Errores:      +1
  Costo: $0.0500 USD
  Duración: 180.5 seg
```

- [ ] **Paso 2: Inspeccionar BD**

Abre `data/colegios.db` con DB Browser for SQLite y revisa:
- Tabla `colegios`: las 5 filas procesadas tienen `estado` distinto a `descubierto`.
- Las que dicen `enriquecido` tienen `web`, `correo_destinatario`, y `perfil_pedagogico` (JSON) llenos.
- Tabla `registro_ejecuciones`: nueva fila con `modulo='enriquecer'`.

- [ ] **Paso 3: Si todo bien, escalar a 30/día**

Para procesar los 3.116 colegios completos, vas a correr ~104 veces de 30 cada uno = ~3-4 meses si lo haces manual diario, o 1-2 días si lo dejas correr múltiples veces seguidas.

Para correr en lotes consecutivos:
```powershell
for ($i=1; $i -le 10; $i++) {
    .\.venv\Scripts\python.exe correr_modulo.py enriquecer --max 30
    Start-Sleep -Seconds 5
}
```
(Esto procesa 300 colegios en una sesión.)

**Costo esperado por lote de 30:** ~$0.30-$0.50 USD. Para los 3.116 totales: $30-$50 USD.

---

## Verificación final del Plan 3

- [ ] Brave API key configurada en `config/.env`
- [ ] `pytest tests/ -v` → todos verdes (~140+ tests)
- [ ] Smoke test con 5 colegios funciona end-to-end
- [ ] BD muestra colegios `enriquecido` con perfil pedagógico clasificado
- [ ] Costo por colegio enriquecido ≤ $0.02 USD

Si todo se cumple, **Plan 3 está completo** y pasamos al **Plan 4** (Generación de HV personalizada + Envío Gmail).

---

## Notas para el implementador

- **Brave free tier:** 1 query/segundo. Si en algún momento procesamos muchos colegios sin web cacheada, podríamos chocar con rate limit. Por ahora no necesitamos throttling explícito (el orquestador procesa secuencialmente).
- **Concurrencia con asyncio:** el spec menciona 5 paralelos. Por ahora secuencial para simplificar; agregar asyncio en una iteración posterior si es muy lento.
- **HTML parsing failures:** algunos sitios tienen JavaScript pesado y el HTML descargado está vacío. Esto resulta en "sin_correo". Aceptable para v1; playwright sería el fallback en versión futura.
- **Costos:** Claude Sonnet 4.6 a $3/M input + $15/M output. Un colegio promedio: ~3000 tokens input + 200 tokens output = ~$0.012 USD por clasificación.
