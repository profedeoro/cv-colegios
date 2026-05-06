from pathlib import Path
import pytest
from modulos.scrapers.men import parsear_men, REGIONES_OBJETIVO

FIXTURE = Path(__file__).parent / "fixtures" / "men_sample.csv"


def test_parsear_men_filtra_solo_no_oficiales_de_regiones_objetivo():
    colegios = parsear_men(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Colegio San Tarsicio" in nombres
    assert "Liceo Campestre" in nombres
    assert "Colegio Bilingüe Bay" in nombres


def test_envigado_es_antioquia_y_se_incluye():
    """Envigado es Antioquia → cualquier colegio no oficial en Envigado debe entrar."""
    colegios = parsear_men(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Escuela Rural" in nombres


def test_barranquilla_se_incluye_pero_resto_de_atlantico_no():
    """De Atlántico solo entra Barranquilla, no otros municipios."""
    colegios = parsear_men(FIXTURE)
    ciudades = [c.ciudad for c in colegios if c.departamento.upper().startswith("ATL")]
    assert all(c.upper() == "BARRANQUILLA" for c in ciudades)


def test_oficial_se_excluye():
    colegios = parsear_men(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Escuela Pública Norte" not in nombres


def test_otras_regiones_se_excluyen():
    colegios = parsear_men(FIXTURE)
    nombres = [c.nombre for c in colegios]
    assert "Colegio Privado Cali" not in nombres


def test_fuente_es_men():
    colegios = parsear_men(FIXTURE)
    assert all(c.fuente == "MEN" for c in colegios)


def test_nit_se_preserva():
    colegios = parsear_men(FIXTURE)
    nits = {c.nit for c in colegios}
    assert "800123456" in nits


def test_falla_si_csv_no_existe(tmp_path):
    with pytest.raises(FileNotFoundError):
        parsear_men(tmp_path / "no_existe.csv")
