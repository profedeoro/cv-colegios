from pathlib import Path
from modulos.scrapers.conaced import parsear_html_conaced, scrape_conaced

FIXTURE = (Path(__file__).parent / "fixtures" / "conaced_sample.html").read_text(encoding="utf-8")


def test_parsear_extrae_colegios_con_ciudad_y_depto():
    colegios = parsear_html_conaced(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Colegio Calasanz Bogotá" in nombres


def test_filtra_solo_regiones_objetivo():
    colegios = parsear_html_conaced(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Colegio Berchmans" not in nombres
    assert "Colegio Calasanz Bogotá" in nombres
    assert "Colegio San José de las Vegas" in nombres


def test_scrape_usa_http(httpx_mock):
    httpx_mock.add_response(url="https://www.conaced.edu.co/colegios", html=FIXTURE)
    colegios = scrape_conaced()
    assert len(colegios) == 2
