import pytest
from modulos.db import conectar, inicializar_db, insertar_colegio, contar_colegios


def test_insertar_colegio_nuevo(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    insertar_colegio(ruta, nombre="Colegio San Tarsicio", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="MEN", nit="800123456-7")
    assert contar_colegios(ruta) == 1


def test_insertar_duplicado_por_nit_no_duplica(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    insertar_colegio(ruta, nombre="Colegio X", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="MEN", nit="800-1")
    insertar_colegio(ruta, nombre="Otro Nombre del mismo colegio", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="UNCOLI", nit="800-1")
    assert contar_colegios(ruta) == 1


def test_insertar_duplicado_por_nombre_normalizado(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    insertar_colegio(ruta, nombre="Colegio San José", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="MEN")
    insertar_colegio(ruta, nombre="COLEGIO SAN JOSE S.A.S.", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="UNCOLI")
    assert contar_colegios(ruta) == 1


def test_mismo_nombre_distinta_ciudad_son_distintos(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    insertar_colegio(ruta, nombre="Colegio San José", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="MEN")
    insertar_colegio(ruta, nombre="Colegio San José", ciudad="Medellín",
                     departamento="Antioquia", fuente="MEN")
    assert contar_colegios(ruta) == 2


def test_dedup_acumula_fuente(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    insertar_colegio(ruta, nombre="Colegio X", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="MEN")
    insertar_colegio(ruta, nombre="Colegio X", ciudad="Bogotá",
                     departamento="Bogotá D.C.", fuente="UNCOLI")
    conn = conectar(ruta)
    fuente = conn.execute("SELECT fuente FROM colegios").fetchone()["fuente"]
    conn.close()
    assert "MEN" in fuente and "UNCOLI" in fuente
