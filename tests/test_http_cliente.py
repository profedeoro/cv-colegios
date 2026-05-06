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
