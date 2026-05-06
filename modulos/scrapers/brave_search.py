"""Wrapper sobre la API de Brave Search.

Tier gratis: 1 query/segundo, ~2.000 queries/mes.
Docs: https://api.search.brave.com/app/documentation/web-search/get-started
"""
import httpx

URL_API = "https://api.search.brave.com/res/v1/web/search"


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
