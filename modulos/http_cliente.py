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
