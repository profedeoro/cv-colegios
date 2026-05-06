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
