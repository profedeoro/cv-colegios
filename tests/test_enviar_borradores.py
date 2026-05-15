"""Tests del orquestador `modulos/enviar_borradores.py`.

Cubre:
- ejecutar() con cola vacía → no llama a Gmail, registra ejecución vacía.
- 2 borradores OK → ambos marcados subido, ambos colegios pasan a borrador_creado.
- HttpError con "Invalid 'to' header" → borrador marcado fallo, colegio
  transicionado a `correo_invalido` (estado terminal), contado aparte.
- HttpError genérico → borrador marcado fallo, colegio queda en enriquecido.
- Excepción inesperada → borrador marcado fallo, colegio queda en enriquecido.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from modulos.db import (
    borradores_listos_para_subir,
    conectar,
    inicializar_db,
    insertar_borrador,
    insertar_colegio,
    marcar_enriquecido,
    obtener_estado,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _bd(tmp_path: Path) -> Path:
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    return ruta


def _colegio_con_borrador(
    bd: Path,
    *,
    nombre: str = "Colegio Test",
    correo_destinatario: str = "rector@x.edu.co",
    ruta_pdf_hv: str | None = None,
) -> tuple[int, int]:
    cid = insertar_colegio(
        bd, nombre=nombre, ciudad="Bogotá",
        departamento="Bogotá D.C.", fuente="MEN",
    )
    marcar_enriquecido(
        bd, cid,
        web="https://x.edu.co",
        correo="info@x.edu.co",
        correo_destinatario=correo_destinatario,
        perfil_pedagogico={"bilingue": False},
        palabras_clave=["x"],
    )
    bid = insertar_borrador(
        bd, cid,
        tipo="inicial",
        asunto=f"Postulación docente — Daniel — {nombre}",
        cuerpo_carta="Estimado equipo directivo,",
        ruta_pdf_hv=ruta_pdf_hv or f"/tmp/{nombre}.pdf",
    )
    return cid, bid


def _http_error(status: int, body: str) -> HttpError:
    """Construye un HttpError realista para los tests."""
    resp = MagicMock(status=status, reason="Bad Request")
    return HttpError(resp, body.encode("utf-8"))


# ---------------------------------------------------------------------------
# ejecutar — cola vacía
# ---------------------------------------------------------------------------

def test_ejecutar_sin_borradores_no_llama_a_gmail(tmp_path):
    from modulos import enviar_borradores

    bd = _bd(tmp_path)
    service_mock = MagicMock(name="gmail_service")

    with patch.object(enviar_borradores, "obtener_servicio_gmail", return_value=service_mock) as p_serv, \
         patch.object(enviar_borradores, "crear_borrador") as p_crear:
        resumen = enviar_borradores.ejecutar(bd, ruta_token="ignored")

    assert resumen["total"] == 0
    assert resumen["subidos"] == 0
    assert resumen["fallos"] == 0
    assert resumen["correo_invalido"] == 0
    p_serv.assert_called_once()
    p_crear.assert_not_called()

    # Aun así se debe registrar la ejecución (ok).
    conn = conectar(bd)
    try:
        ej = conn.execute(
            "SELECT estado, colegios_procesados FROM registro_ejecuciones "
            "WHERE modulo = 'enviar_borradores' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    assert ej is not None
    assert ej["estado"] == "ok"
    assert ej["colegios_procesados"] == 0


# ---------------------------------------------------------------------------
# ejecutar — happy path: dos borradores OK
# ---------------------------------------------------------------------------

def test_ejecutar_dos_borradores_ambos_subidos(tmp_path):
    from modulos import enviar_borradores

    bd = _bd(tmp_path)
    cid_a, bid_a = _colegio_con_borrador(bd, nombre="Colegio Alfa",
                                          correo_destinatario="rector_a@a.edu.co")
    cid_b, bid_b = _colegio_con_borrador(bd, nombre="Colegio Beta",
                                          correo_destinatario="rector_b@b.edu.co")
    service_mock = MagicMock(name="gmail_service")

    # Devolver ids distintos por llamada.
    def fake_crear(service, *, destinatario, asunto, cuerpo, adjunto_pdf):
        if "alfa" in destinatario.lower() or destinatario.startswith("rector_a"):
            return ("draft-A", "thread-A")
        return ("draft-B", "thread-B")

    with patch.object(enviar_borradores, "obtener_servicio_gmail", return_value=service_mock), \
         patch.object(enviar_borradores, "crear_borrador", side_effect=fake_crear) as p_crear:
        resumen = enviar_borradores.ejecutar(bd, ruta_token="ignored")

    assert resumen == {"total": 2, "subidos": 2, "fallos": 0, "correo_invalido": 0}
    assert p_crear.call_count == 2

    # Borradores marcados subido con su draft_id.
    conn = conectar(bd)
    try:
        rows = conn.execute(
            "SELECT id, estado, gmail_draft_id FROM borradores ORDER BY id"
        ).fetchall()
        # Colegios transicionaron a borrador_creado con sus ids de Gmail.
        col_a = conn.execute(
            "SELECT estado, gmail_draft_id, gmail_thread_id FROM colegios WHERE id = ?", (cid_a,)
        ).fetchone()
        col_b = conn.execute(
            "SELECT estado, gmail_draft_id, gmail_thread_id FROM colegios WHERE id = ?", (cid_b,)
        ).fetchone()
        ej = conn.execute(
            "SELECT estado, colegios_procesados FROM registro_ejecuciones "
            "WHERE modulo = 'enviar_borradores' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    assert [r["estado"] for r in rows] == ["subido", "subido"]
    assert all(r["gmail_draft_id"] for r in rows)

    assert col_a["estado"] == "borrador_creado"
    assert col_a["gmail_draft_id"] == "draft-A"
    assert col_a["gmail_thread_id"] == "thread-A"

    assert col_b["estado"] == "borrador_creado"
    assert col_b["gmail_draft_id"] == "draft-B"
    assert col_b["gmail_thread_id"] == "thread-B"

    assert ej["estado"] == "ok"
    assert ej["colegios_procesados"] == 2


def test_ejecutar_pasa_destinatario_asunto_cuerpo_y_adjunto_a_crear_borrador(tmp_path):
    """ejecutar() debe propagar correctamente los campos del borrador a crear_borrador()."""
    from modulos import enviar_borradores

    bd = _bd(tmp_path)
    cid, bid = _colegio_con_borrador(
        bd, nombre="Colegio Gamma",
        correo_destinatario="rector@gamma.edu.co",
        ruta_pdf_hv="/tmp/gamma.pdf",
    )
    service_mock = MagicMock()

    with patch.object(enviar_borradores, "obtener_servicio_gmail", return_value=service_mock), \
         patch.object(enviar_borradores, "crear_borrador",
                      return_value=("d-1", "t-1")) as p_crear:
        enviar_borradores.ejecutar(bd, ruta_token="ignored")

    p_crear.assert_called_once()
    _, kwargs = p_crear.call_args
    assert kwargs["destinatario"] == "rector@gamma.edu.co"
    assert "Colegio Gamma" in kwargs["asunto"]
    assert kwargs["cuerpo"] == "Estimado equipo directivo,"
    assert kwargs["adjunto_pdf"] == "/tmp/gamma.pdf"


# ---------------------------------------------------------------------------
# ejecutar — correo inválido (HttpError 400 + "Invalid 'to' header")
# ---------------------------------------------------------------------------

def test_ejecutar_correo_invalido_marca_fallo_y_cuenta_aparte(tmp_path):
    from modulos import enviar_borradores

    bd = _bd(tmp_path)
    cid, bid = _colegio_con_borrador(
        bd, nombre="Colegio Mal Correo",
        correo_destinatario="no-existe@inexistente.tld",
    )
    service_mock = MagicMock()

    err = _http_error(400, '{"error": {"message": "Invalid \\u0027to\\u0027 header"}}')

    with patch.object(enviar_borradores, "obtener_servicio_gmail", return_value=service_mock), \
         patch.object(enviar_borradores, "crear_borrador", side_effect=err):
        resumen = enviar_borradores.ejecutar(bd, ruta_token="ignored")

    assert resumen["total"] == 1
    assert resumen["subidos"] == 0
    assert resumen["correo_invalido"] == 1
    # El colegio transiciona al estado terminal `correo_invalido` y se cuenta
    # en `resumen["correo_invalido"]`, separado del contador `fallos`.
    assert resumen["fallos"] == 0

    conn = conectar(bd)
    try:
        row = conn.execute(
            "SELECT estado, error_mensaje FROM borradores WHERE id = ?", (bid,),
        ).fetchone()
    finally:
        conn.close()
    assert row["estado"] == "fallo"
    assert "correo" in (row["error_mensaje"] or "").lower() or \
           "invalid" in (row["error_mensaje"] or "").lower()

    # El colegio transiciona al estado terminal `correo_invalido`.
    assert obtener_estado(bd, cid) == "correo_invalido"


# ---------------------------------------------------------------------------
# ejecutar — HttpError genérico (no relacionado con correo inválido)
# ---------------------------------------------------------------------------

def test_ejecutar_http_error_generico_marca_fallo_pero_no_correo_invalido(tmp_path):
    from modulos import enviar_borradores

    bd = _bd(tmp_path)
    cid, bid = _colegio_con_borrador(bd, nombre="Colegio HTTP 500")
    service_mock = MagicMock()

    err = _http_error(500, '{"error": {"message": "Backend Error"}}')

    with patch.object(enviar_borradores, "obtener_servicio_gmail", return_value=service_mock), \
         patch.object(enviar_borradores, "crear_borrador", side_effect=err):
        resumen = enviar_borradores.ejecutar(bd, ruta_token="ignored")

    assert resumen["total"] == 1
    assert resumen["subidos"] == 0
    assert resumen["fallos"] == 1
    assert resumen["correo_invalido"] == 0

    conn = conectar(bd)
    try:
        row = conn.execute(
            "SELECT estado, error_mensaje FROM borradores WHERE id = ?", (bid,),
        ).fetchone()
        # La ejecución debe registrarse como 'error' (hay fallos genéricos).
        ej = conn.execute(
            "SELECT estado FROM registro_ejecuciones "
            "WHERE modulo = 'enviar_borradores' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    assert row["estado"] == "fallo"
    assert row["error_mensaje"]
    assert obtener_estado(bd, cid) == "enriquecido"
    assert ej["estado"] == "error"


# ---------------------------------------------------------------------------
# ejecutar — excepción inesperada (no HttpError)
# ---------------------------------------------------------------------------

def test_ejecutar_excepcion_inesperada_marca_fallo(tmp_path):
    from modulos import enviar_borradores

    bd = _bd(tmp_path)
    cid, bid = _colegio_con_borrador(bd, nombre="Colegio Boom")
    service_mock = MagicMock()

    with patch.object(enviar_borradores, "obtener_servicio_gmail", return_value=service_mock), \
         patch.object(enviar_borradores, "crear_borrador",
                      side_effect=RuntimeError("algo se rompió")):
        resumen = enviar_borradores.ejecutar(bd, ruta_token="ignored")

    assert resumen["total"] == 1
    assert resumen["subidos"] == 0
    assert resumen["fallos"] == 1
    assert resumen["correo_invalido"] == 0

    conn = conectar(bd)
    try:
        row = conn.execute(
            "SELECT estado, error_mensaje FROM borradores WHERE id = ?", (bid,),
        ).fetchone()
    finally:
        conn.close()
    assert row["estado"] == "fallo"
    assert "algo se rompió" in (row["error_mensaje"] or "")
    assert obtener_estado(bd, cid) == "enriquecido"


# ---------------------------------------------------------------------------
# ejecutar — mezcla: un éxito + un correo inválido + un error genérico
# ---------------------------------------------------------------------------

def test_ejecutar_mezcla_de_resultados(tmp_path):
    from modulos import enviar_borradores

    bd = _bd(tmp_path)
    cid_ok, bid_ok = _colegio_con_borrador(bd, nombre="Colegio OK",
                                            correo_destinatario="ok@ok.edu.co")
    cid_mal, bid_mal = _colegio_con_borrador(bd, nombre="Colegio Mal",
                                              correo_destinatario="mal@bad")
    cid_err, bid_err = _colegio_con_borrador(bd, nombre="Colegio Err",
                                              correo_destinatario="err@err.edu.co")
    service_mock = MagicMock()

    err_invalido = _http_error(400, '{"error": {"message": "Invalid \'to\' header"}}')
    err_otro = _http_error(503, '{"error": {"message": "Service Unavailable"}}')

    def fake_crear(service, *, destinatario, asunto, cuerpo, adjunto_pdf):
        if destinatario == "ok@ok.edu.co":
            return ("draft-ok", "thread-ok")
        if destinatario == "mal@bad":
            raise err_invalido
        raise err_otro

    with patch.object(enviar_borradores, "obtener_servicio_gmail", return_value=service_mock), \
         patch.object(enviar_borradores, "crear_borrador", side_effect=fake_crear):
        resumen = enviar_borradores.ejecutar(bd, ruta_token="ignored")

    assert resumen == {"total": 3, "subidos": 1, "fallos": 1, "correo_invalido": 1}

    conn = conectar(bd)
    try:
        estados = {
            r["id"]: r["estado"]
            for r in conn.execute(
                "SELECT id, estado FROM borradores ORDER BY id"
            ).fetchall()
        }
        cols = {
            cid: conn.execute("SELECT estado FROM colegios WHERE id = ?", (cid,)).fetchone()["estado"]
            for cid in (cid_ok, cid_mal, cid_err)
        }
    finally:
        conn.close()

    assert estados[bid_ok] == "subido"
    assert estados[bid_mal] == "fallo"
    assert estados[bid_err] == "fallo"
    assert cols[cid_ok] == "borrador_creado"
    assert cols[cid_mal] == "correo_invalido"  # estado terminal por correo inválido
    assert cols[cid_err] == "enriquecido"


# ---------------------------------------------------------------------------
# Detector de correo inválido — unit test directo
# ---------------------------------------------------------------------------

def test_es_correo_invalido_reconoce_invalid_to_header():
    from modulos.enviar_borradores import _es_correo_invalido

    err = _http_error(400, '{"error": {"message": "Invalid \'to\' header"}}')
    assert _es_correo_invalido(err) is True


def test_es_correo_invalido_ignora_errores_5xx():
    from modulos.enviar_borradores import _es_correo_invalido

    err = _http_error(500, '{"error": {"message": "Backend Error"}}')
    assert _es_correo_invalido(err) is False


def test_es_correo_invalido_ignora_400_no_relacionado():
    from modulos.enviar_borradores import _es_correo_invalido

    err = _http_error(400, '{"error": {"message": "Quota exceeded"}}')
    assert _es_correo_invalido(err) is False
