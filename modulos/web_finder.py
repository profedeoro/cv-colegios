"""Encuentra el sitio web oficial de un colegio usando Brave Search.

Heurística:
1. Descarta redes sociales y directorios genéricos (blacklist).
2. Calcula similitud entre el nombre del colegio y cada resultado:
   tokens distintivos del nombre que aparecen en el título/URL/descripción.
3. Solo acepta resultados con similitud >= UMBRAL_SIMILITUD (50%).
4. Entre los que pasan, prefiere .edu.co; si hay empate, mayor score gana.
5. Si NINGÚN resultado pasa el umbral, devuelve None (mejor sin web que con web equivocada).
"""
import re
import unicodedata
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

# Palabras genéricas y abreviaturas comunes que NO son distintivas.
PALABRAS_NO_DISTINTIVAS = {
    "colegio", "col", "fund", "fundacion",
    "institucion", "instituto", "inst", "ie", "ied", "iet",
    "educativa", "educativo", "educacion",
    "gimnasio", "gimn", "gym",
    "liceo", "lic",
    "escuela", "esc",
    "centro", "ctr", "cent",
    "preescolar", "prees", "preescolares", "infantil", "inf",
    "jardin", "jard",
    "guarderia",
    "nacional", "nal", "nac",
    "distrital", "dist",
    "municipal", "mun",
    "publico", "publica",
    "privado", "privada",
    "regional", "reg",
    # Conectores comunes
    "del", "los", "las", "san", "santa", "santo",
    # Ciudad / región (a veces se filtra el nombre con ciudad)
    "bogota", "medellin", "cali", "barranquilla",
}

UMBRAL_SIMILITUD = 0.5


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


def _normalizar_para_match(texto: str) -> str:
    """Lowercase + sin acentos. Para comparación tolerante."""
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_acentos.lower()


def _tokens_distintivos(nombre: str) -> list[str]:
    """Extrae tokens distintivos del nombre del colegio.

    Lowercase, sin acentos, sin palabras genéricas/abreviaturas, mín 4 chars.
    """
    norm = _normalizar_para_match(nombre)
    tokens = re.findall(r"\w+", norm)
    return [t for t in tokens if t not in PALABRAS_NO_DISTINTIVAS and len(t) >= 4]


def _texto_resultado(item: dict) -> str:
    """Junta título + URL + descripción del resultado, normalizado para matching."""
    partes = [
        item.get("title", ""),
        item.get("url", ""),
        item.get("description", ""),
    ]
    return _normalizar_para_match(" ".join(partes))


def _score_match(nombre: str, item: dict) -> float:
    """Fracción de tokens distintivos del nombre que aparecen en el item.

    Usa substring match (no word match) porque las URLs concatenan palabras
    (ej: "santamaria.edu.co" debe matchear "santa" y "maria").
    """
    tokens = _tokens_distintivos(nombre)
    if not tokens:
        return 0.0
    texto = _texto_resultado(item)
    matches = sum(1 for t in tokens if t in texto)
    return matches / len(tokens)


def encontrar_web(nombre_colegio: str, ciudad: str, api_key: str) -> str | None:
    """Busca el sitio web del colegio en Brave. Devuelve URL o None.

    Solo acepta resultados con similitud >= UMBRAL_SIMILITUD para evitar
    asignar emails de colegios equivocados.
    """
    query = f"{nombre_colegio} {ciudad} colegio sitio oficial"
    resultados = buscar_brave(query=query, api_key=api_key, count=10)

    # 1. Filtrar dominios blacklisted
    aceptables = [r for r in resultados if _es_aceptable(r.get("url", ""))]
    if not aceptables:
        return None

    # 2. Calcular score y filtrar por umbral
    suficientes = [(r, _score_match(nombre_colegio, r)) for r in aceptables]
    suficientes = [(r, s) for r, s in suficientes if s >= UMBRAL_SIMILITUD]
    if not suficientes:
        return None  # mejor None que web equivocada

    # 3. Preferir .edu.co; en empate, mayor score gana
    edu_co = [(r, s) for r, s in suficientes if _es_edu_co(r["url"])]
    if edu_co:
        edu_co.sort(key=lambda x: -x[1])
        return edu_co[0][0]["url"]
    suficientes.sort(key=lambda x: -x[1])
    return suficientes[0][0]["url"]
