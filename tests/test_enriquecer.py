from unittest.mock import patch, MagicMock
import pytest
from modulos.enriquecer import procesar_colegio
from modulos.db import inicializar_db, insertar_colegio, conectar


def _bd_con_colegio(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    cid = insertar_colegio(bd, nombre="Colegio Test", ciudad="Bogotá",
                            departamento="Bogotá D.C.", fuente="MEN")
    return bd, cid


def test_procesar_colegio_marca_enriquecido_si_todo_ok(tmp_path):
    bd, cid = _bd_con_colegio(tmp_path)
    colegio = {"id": cid, "nombre": "Colegio Test", "ciudad": "Bogotá",
               "departamento": "Bogotá D.C.", "web": None}

    cliente_claude = MagicMock()
    cliente_claude.preguntar.return_value = (
        '{"bilingue": true, "idioma_segundo": "inglés", "religioso": false,'
        ' "denominacion": null, "ib": false, "montessori": false,'
        ' "enfoque_deportivo": false, "enfoque_tecnico": false, "enfasis_tic": true,'
        ' "tamano_estimado": "mediano", "palabras_clave": ["bilingüe", "innovación"]}',
        0.01,
    )

    with patch("modulos.enriquecer.encontrar_web", return_value="https://test.edu.co/"), \
         patch("modulos.enriquecer.fetch_html", return_value="<html><body>info@test.edu.co rector@test.edu.co</body></html>"), \
         patch("modulos.enriquecer.validar_dominio", return_value=True):
        resultado = procesar_colegio(bd, colegio, cliente_claude, brave_api_key="BSA-test")

    assert resultado["estado_final"] == "enriquecido"
    conn = conectar(bd)
    row = conn.execute("SELECT estado, web, correo_destinatario FROM colegios WHERE id = ?", (cid,)).fetchone()
    conn.close()
    assert row["estado"] == "enriquecido"
    assert row["web"] == "https://test.edu.co/"
    assert row["correo_destinatario"] == "rector@test.edu.co"


def test_procesar_colegio_sin_web_marca_sin_correo(tmp_path):
    bd, cid = _bd_con_colegio(tmp_path)
    colegio = {"id": cid, "nombre": "Colegio Test", "ciudad": "Bogotá",
               "departamento": "Bogotá D.C.", "web": None}
    cliente_claude = MagicMock()

    with patch("modulos.enriquecer.encontrar_web", return_value=None):
        resultado = procesar_colegio(bd, colegio, cliente_claude, brave_api_key="BSA-test")

    assert resultado["estado_final"] == "sin_correo"
    conn = conectar(bd)
    estado = conn.execute("SELECT estado FROM colegios WHERE id = ?", (cid,)).fetchone()["estado"]
    conn.close()
    assert estado == "sin_correo"


def test_procesar_colegio_sin_email_valido_marca_sin_correo(tmp_path):
    bd, cid = _bd_con_colegio(tmp_path)
    colegio = {"id": cid, "nombre": "Colegio Test", "ciudad": "Bogotá",
               "departamento": "Bogotá D.C.", "web": None}
    cliente_claude = MagicMock()

    with patch("modulos.enriquecer.encontrar_web", return_value="https://x.edu.co/"), \
         patch("modulos.enriquecer.fetch_html", return_value="<html><body>sin emails aqui</body></html>"):
        resultado = procesar_colegio(bd, colegio, cliente_claude, brave_api_key="BSA-test")

    assert resultado["estado_final"] == "sin_correo"


def test_procesar_colegio_email_dominio_invalido_marca_sin_correo(tmp_path):
    bd, cid = _bd_con_colegio(tmp_path)
    colegio = {"id": cid, "nombre": "Colegio Test", "ciudad": "Bogotá",
               "departamento": "Bogotá D.C.", "web": None}
    cliente_claude = MagicMock()

    with patch("modulos.enriquecer.encontrar_web", return_value="https://x.edu.co/"), \
         patch("modulos.enriquecer.fetch_html", return_value="<html><body>info@dominio-falso-12345.tld</body></html>"), \
         patch("modulos.enriquecer.validar_dominio", return_value=False):
        resultado = procesar_colegio(bd, colegio, cliente_claude, brave_api_key="BSA-test")

    assert resultado["estado_final"] == "sin_correo"


def test_procesar_colegio_falla_fetch_incrementa_intento(tmp_path):
    bd, cid = _bd_con_colegio(tmp_path)
    colegio = {"id": cid, "nombre": "Colegio Test", "ciudad": "Bogotá",
               "departamento": "Bogotá D.C.", "web": None}
    cliente_claude = MagicMock()

    from modulos.http_cliente import HttpError
    with patch("modulos.enriquecer.encontrar_web", return_value="https://x.edu.co/"), \
         patch("modulos.enriquecer.fetch_html", side_effect=HttpError("timeout")):
        resultado = procesar_colegio(bd, colegio, cliente_claude, brave_api_key="BSA-test")

    assert resultado["estado_final"] == "error"
    conn = conectar(bd)
    intentos = conn.execute("SELECT intentos_enriquecer FROM colegios WHERE id = ?", (cid,)).fetchone()[0]
    conn.close()
    assert intentos == 1
