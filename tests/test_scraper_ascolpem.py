from pathlib import Path
from modulos.scrapers.ascolpem import parsear_html_ascolpem, scrape_ascolpem

FIXTURE = (Path(__file__).parent / "fixtures" / "ascolpem_sample.html").read_text(encoding="utf-8")


def test_parsear_extrae_de_tabla():
    colegios = parsear_html_ascolpem(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Colegio Marymount" in nombres


def test_filtra_regiones_objetivo():
    colegios = parsear_html_ascolpem(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Colegio Andino Cartagena" not in nombres
    assert "Liceo Pino Verde" not in nombres
    assert "Colegio Marymount" in nombres


def test_scrape_devuelve_lista_vacia_en_404(httpx_mock):
    """Si la URL de ASCOLPEM no existe o cambia, el scraper no debe romper el pipeline."""
    httpx_mock.add_response(
        url="https://www.ascolpem.com/afiliados",
        status_code=404,
    )
    colegios = scrape_ascolpem()
    assert colegios == []
