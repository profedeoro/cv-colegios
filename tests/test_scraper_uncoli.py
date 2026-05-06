from pathlib import Path
import pytest
from modulos.scrapers.uncoli import parsear_html_uncoli, scrape_uncoli

FIXTURE = (Path(__file__).parent / "fixtures" / "uncoli_sample.html").read_text(encoding="utf-8")


def test_parsear_extrae_nombres():
    colegios = parsear_html_uncoli(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "COLEGIO ANGLO COLOMBIANO" in nombres
    assert "COLEGIO LOS NOGALES" in nombres
    assert "GIMNASIO MODERNO" in nombres


def test_parsear_asigna_ciudad_bogota_y_departamento():
    colegios = parsear_html_uncoli(FIXTURE)
    assert all(c.ciudad == "Bogotá" for c in colegios)
    assert all(c.departamento == "Bogotá D.C." for c in colegios)


def test_parsear_extrae_web_si_disponible():
    colegios = parsear_html_uncoli(FIXTURE)
    web_anglo = next(c.web for c in colegios if "ANGLO" in c.nombre)
    assert web_anglo == "https://www.anglocolombiano.edu.co/"


def test_parsear_fuente_es_uncoli():
    colegios = parsear_html_uncoli(FIXTURE)
    assert all(c.fuente == "UNCOLI" for c in colegios)


def test_scrape_uncoli_usa_http(httpx_mock):
    httpx_mock.add_response(
        url="https://www.uncoli.org/colegios-asociados/",
        html=FIXTURE,
    )
    colegios = scrape_uncoli()
    assert len(colegios) == 3
