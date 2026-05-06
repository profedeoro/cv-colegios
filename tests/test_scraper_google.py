import re
import pytest
from modulos.scrapers.google_cse import buscar_google, queries_a_colegios


def test_buscar_google_arma_url_correcta(httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r"https://www\.googleapis\.com/customsearch/v1.*"),
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
        url=re.compile(r"https://www\.googleapis\.com/customsearch/v1.*"),
        json={},
    )
    resultados = buscar_google(query="x", api_key="k", engine_id="e")
    assert resultados == []


def test_queries_a_colegios_convierte_resultados(httpx_mock):
    """Los items de Google Search se convierten a ColegioInfo con ciudad inferida."""
    httpx_mock.add_response(
        url=re.compile(r".*googleapis.*"),
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
