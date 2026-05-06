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
                continue
            ciudad, depto = ubicacion
            colegios.append(ColegioInfo(
                nombre=titulo,
                ciudad=ciudad,
                departamento=depto,
                fuente="Google",
                web=link or None,
            ))
    return colegios
