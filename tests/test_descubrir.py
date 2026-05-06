import json
from pathlib import Path
from unittest.mock import patch
import pytest
from modulos.descubrir import ejecutar
from modulos.db import inicializar_db, contar_colegios
from modulos.scrapers.tipos import ColegioInfo


def _bd_inicializada(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    return bd


def test_descubrir_inserta_colegios_de_men(tmp_path):
    bd = _bd_inicializada(tmp_path)
    csv_men = tmp_path / "men.csv"
    csv_men.write_text(
        "NIT,NOMBRE_ESTABLECIMIENTO,MUNICIPIO,DEPARTAMENTO,NATURALEZA,NIVEL\n"
        "800-1,Colegio Test,BOGOTÁ D.C.,BOGOTÁ D.C.,NO OFICIAL,SECUNDARIA\n",
        encoding="utf-8",
    )

    with patch("modulos.descubrir.scrape_uncoli", return_value=[]), \
         patch("modulos.descubrir.scrape_conaced", return_value=[]), \
         patch("modulos.descubrir.scrape_ascolpem", return_value=[]), \
         patch("modulos.descubrir.queries_a_colegios", return_value=[]):
        ejecutar(ruta_bd=bd, ruta_csv_men=csv_men, queries_path=None,
                 google_api_key=None, google_engine_id=None)

    assert contar_colegios(bd) == 1


def test_descubrir_acumula_fuentes_en_dedup(tmp_path):
    bd = _bd_inicializada(tmp_path)
    csv_men = tmp_path / "men.csv"
    csv_men.write_text(
        "NIT,NOMBRE_ESTABLECIMIENTO,MUNICIPIO,DEPARTAMENTO,NATURALEZA,NIVEL\n"
        "800-1,Colegio Compartido,BOGOTÁ D.C.,BOGOTÁ D.C.,NO OFICIAL,SECUNDARIA\n",
        encoding="utf-8",
    )
    miembro_uncoli = ColegioInfo(
        nombre="Colegio Compartido", ciudad="Bogotá",
        departamento="Bogotá D.C.", fuente="UNCOLI",
    )

    with patch("modulos.descubrir.scrape_uncoli", return_value=[miembro_uncoli]), \
         patch("modulos.descubrir.scrape_conaced", return_value=[]), \
         patch("modulos.descubrir.scrape_ascolpem", return_value=[]), \
         patch("modulos.descubrir.queries_a_colegios", return_value=[]):
        ejecutar(ruta_bd=bd, ruta_csv_men=csv_men, queries_path=None,
                 google_api_key=None, google_engine_id=None)

    assert contar_colegios(bd) == 1  # NO se duplicó
    from modulos.db import conectar
    conn = conectar(bd)
    fuente = conn.execute("SELECT fuente FROM colegios").fetchone()["fuente"]
    conn.close()
    assert "MEN" in fuente
    assert "UNCOLI" in fuente


def test_descubrir_no_falla_si_men_no_existe(tmp_path):
    """Si el CSV del MEN no está, el descubrimiento sigue con las otras fuentes."""
    bd = _bd_inicializada(tmp_path)
    miembro = ColegioInfo(
        nombre="Solo UNCOLI", ciudad="Bogotá",
        departamento="Bogotá D.C.", fuente="UNCOLI",
    )
    with patch("modulos.descubrir.scrape_uncoli", return_value=[miembro]), \
         patch("modulos.descubrir.scrape_conaced", return_value=[]), \
         patch("modulos.descubrir.scrape_ascolpem", return_value=[]), \
         patch("modulos.descubrir.queries_a_colegios", return_value=[]):
        ejecutar(ruta_bd=bd, ruta_csv_men=tmp_path / "no_existe.csv",
                 queries_path=None, google_api_key=None, google_engine_id=None)
    assert contar_colegios(bd) == 1


def test_descubrir_registra_ejecucion(tmp_path):
    bd = _bd_inicializada(tmp_path)
    with patch("modulos.descubrir.scrape_uncoli", return_value=[]), \
         patch("modulos.descubrir.scrape_conaced", return_value=[]), \
         patch("modulos.descubrir.scrape_ascolpem", return_value=[]), \
         patch("modulos.descubrir.queries_a_colegios", return_value=[]):
        ejecutar(ruta_bd=bd, ruta_csv_men=tmp_path / "no.csv",
                 queries_path=None, google_api_key=None, google_engine_id=None)
    from modulos.db import ultima_ejecucion_ok
    assert ultima_ejecucion_ok(bd, modulo="descubrir") is not None
