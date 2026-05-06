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
    # Directorios de colegios (replican nombre en URL pero no son sitios reales)
    "educacionencolombia.com.co",
    "buscacolegio.com.co",
    "colegiosencolombia.com",
    "colegiosbogota.co",
    "colegioscolombia.com.co",
    "guiaacademica.com",
    "elempleo.com",
    "computrabajo.com.co",
    "linkedin.com",
    "colegioscolombianos.com",
    "colegioscolombianos.com.co",
    "guiacolegios.com",
    "guiacolegios.com.co",
    "directoriocolegios.com",
    "todocolegios.com",
    "buscocolegio.com",
    "colombiaeducativa.com",
    "36colegios.co",
    "36colegios.com",
    "co.institucioneducativa.info",
    "institucioneducativa.info",
    "datoscolombia.com",
    "micole.net",
    "colegioscolombia.com",
    "moovitapp.com",
    "jimdofree.com",
    "sites.google.com",
    "yelp.com.co",
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

# TLDs de países distintos a Colombia → siempre rechazar.
# Colegios colombianos no usan .es, .com.mx, .com.ar, .com.br, etc.
TLDS_EXTRANJEROS = {
    ".es", ".eus", ".cat",                       # España
    ".com.mx", ".mx", ".edu.mx", ".org.mx",      # México
    ".com.ar", ".ar", ".edu.ar", ".org.ar",      # Argentina
    ".com.br", ".br", ".edu.br",                 # Brasil
    ".cl", ".com.cl",                            # Chile
    ".pe", ".com.pe",                            # Perú
    ".ec", ".com.ec", ".edu.ec",                 # Ecuador
    ".ve", ".com.ve",                            # Venezuela
    ".uy", ".com.uy",                            # Uruguay
    ".py", ".com.py",                            # Paraguay
    ".bo", ".com.bo",                            # Bolivia
    ".cr", ".com.cr",                            # Costa Rica
    ".pa", ".com.pa",                            # Panamá
    ".gt", ".com.gt",                            # Guatemala
    ".do", ".com.do",                            # Dominicana
    ".pr", ".com.pr",                            # Puerto Rico
    ".cu", ".com.cu",                            # Cuba
    ".de", ".fr", ".it", ".pt", ".ch", ".be",    # Europa varios
    ".uk", ".co.uk", ".ac.uk",                   # UK
    ".us", ".edu", ".gov",                       # USA (.edu suele ser US, no Colombia)
    ".ru", ".cn", ".jp", ".in",                  # otros
}


def _es_extranjero(url: str) -> bool:
    """True si la URL termina en un TLD extranjero (no Colombia)."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    if not host:
        return False
    # Quitar puerto si lo hay
    if ":" in host:
        host = host.split(":")[0]
    for tld in TLDS_EXTRANJEROS:
        if host.endswith(tld):
            return True
    return False


def _es_aceptable(url: str) -> bool:
    """True si la URL no es blacklisted ni de un país extranjero."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    if not host:
        return False
    # 1. Rechazar TLDs extranjeros (no Colombia)
    if _es_extranjero(url):
        return False
    # 2. Rechazar dominios blacklisted (match exacto o subdominio)
    for blacklisted in DOMINIOS_BLACKLIST:
        if host == blacklisted or host.endswith("." + blacklisted):
            return False
    return True


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


def _score_match(nombre: str, item: dict) -> tuple[int, float]:
    """Devuelve (matches_absolutos, fracción) — fracción de tokens distintivos
    del nombre que aparecen en el item (substring match en title+url+desc).
    """
    tokens = _tokens_distintivos(nombre)
    if not tokens:
        return (0, 0.0)
    texto = _texto_resultado(item)
    matches = sum(1 for t in tokens if t in texto)
    return (matches, matches / len(tokens))


def encontrar_web(nombre_colegio: str, ciudad: str, api_key: str) -> str | None:
    """Busca el sitio web del colegio en Brave. Devuelve URL o None.

    Reglas estrictas para evitar falsos positivos:
    1. Descartar dominios blacklisted (redes sociales, directorios).
    2. Calcular tokens distintivos del nombre.
    3. Aceptar resultado solo si score >= UMBRAL_SIMILITUD Y matches >= min(2, len(tokens)).
       Esto exige al menos 2 tokens coincidentes para nombres con 2+ palabras distintivas,
       evitando matches falsos cuando solo 1 palabra coincide por coincidencia.
    4. Preferir .edu.co; entre los aceptables, mayor score gana.
    5. Si NINGÚN resultado pasa los filtros → None (mejor sin web que con web errónea).
    """
    query = f"{nombre_colegio} {ciudad} colegio sitio oficial"
    resultados = buscar_brave(query=query, api_key=api_key, count=10)

    aceptables = [r for r in resultados if _es_aceptable(r.get("url", ""))]
    if not aceptables:
        return None

    tokens_total = len(_tokens_distintivos(nombre_colegio))
    matches_minimos = min(2, tokens_total) if tokens_total > 0 else 1

    candidatos_validos = []
    for r in aceptables:
        matches, score = _score_match(nombre_colegio, r)
        if score >= UMBRAL_SIMILITUD and matches >= matches_minimos:
            candidatos_validos.append((r, score))

    if not candidatos_validos:
        return None

    edu_co = [(r, s) for r, s in candidatos_validos if _es_edu_co(r["url"])]
    if edu_co:
        edu_co.sort(key=lambda x: -x[1])
        return edu_co[0][0]["url"]
    candidatos_validos.sort(key=lambda x: -x[1])
    return candidatos_validos[0][0]["url"]
