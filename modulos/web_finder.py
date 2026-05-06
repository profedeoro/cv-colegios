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
    edu_co = [u for u in aceptables if _es_edu_co(u)]
    return edu_co[0] if edu_co else aceptables[0]
