"""Tests para los helpers de BD usados por `enviar_borradores`.

Helpers cubiertos:
- borradores_listos_para_subir
- marcar_borrador_subido
- marcar_borrador_fallo
"""
from pathlib import Path

import pytest

from modulos.db import (
    borradores_listos_para_subir,
    conectar,
    inicializar_db,
    insertar_borrador,
    insertar_colegio,
    marcar_borrador_fallo,
    marcar_borrador_subido,
    marcar_enriquecido,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _bd(tmp_path: Path) -> Path:
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    return ruta


def _enriquecer(bd: Path, cid: int, *, correo_destinatario: str = "rector@x.edu.co") -> None:
    marcar_enriquecido(
        bd, cid,
        web="https://x.edu.co",
        correo="info@x.edu.co",
        correo_destinatario=correo_destinatario,
        perfil_pedagogico={"bilingue": False},
        palabras_clave=["x"],
    )


def _colegio_enriquecido(bd: Path, nombre: str = "Colegio X",
                         correo_destinatario: str = "rector@x.edu.co") -> int:
    cid = insertar_colegio(
        bd, nombre=nombre, ciudad="Bogotá",
        departamento="Bogotá D.C.", fuente="MEN",
    )
    _enriquecer(bd, cid, correo_destinatario=correo_destinatario)
    return cid


# ---------------------------------------------------------------------------
# borradores_listos_para_subir
# ---------------------------------------------------------------------------

def test_borradores_listos_para_subir_devuelve_solo_listos(tmp_path):
    bd = _bd(tmp_path)
    cid = _colegio_enriquecido(bd)
    bid_listo = insertar_borrador(
        bd, cid, tipo="inicial", asunto="A", cuerpo_carta="c",
        ruta_pdf_hv="/tmp/a.pdf",
    )
    # Insertar un segundo borrador y marcarlo como subido (no debe aparecer).
    bid_subido = insertar_borrador(
        bd, cid, tipo="seguimiento", asunto="B", cuerpo_carta="c2",
        ruta_pdf_hv="/tmp/b.pdf",
    )
    marcar_borrador_subido(bd, bid_subido, gmail_draft_id="g-1")

    listos = borradores_listos_para_subir(bd)
    ids = [b["id"] for b in listos]
    assert ids == [bid_listo]


def test_borradores_listos_para_subir_incluye_destinatario_y_campos(tmp_path):
    bd = _bd(tmp_path)
    cid = _colegio_enriquecido(bd, correo_destinatario="rector@colegio.edu.co")
    bid = insertar_borrador(
        bd, cid, tipo="inicial",
        asunto="Postulación docente — Daniel — Colegio X",
        cuerpo_carta="Estimado rector,",
        ruta_pdf_hv="/tmp/hv.pdf",
    )

    listos = borradores_listos_para_subir(bd)
    assert len(listos) == 1
    b = listos[0]
    assert b["id"] == bid
    assert b["colegio_id"] == cid
    assert b["asunto"] == "Postulación docente — Daniel — Colegio X"
    assert b["cuerpo_carta"] == "Estimado rector,"
    assert b["ruta_pdf_hv"] == "/tmp/hv.pdf"
    # El join con colegios debe traer el correo_destinatario.
    assert b["correo_destinatario"] == "rector@colegio.edu.co"


def test_borradores_listos_para_subir_vacio_sin_pendientes(tmp_path):
    bd = _bd(tmp_path)
    assert borradores_listos_para_subir(bd) == []


def test_borradores_listos_para_subir_ordenados_por_fecha_creado(tmp_path):
    bd = _bd(tmp_path)
    cid = _colegio_enriquecido(bd)
    b_viejo = insertar_borrador(
        bd, cid, tipo="inicial", asunto="viejo", cuerpo_carta="c",
        ruta_pdf_hv="/tmp/v.pdf",
    )
    b_nuevo = insertar_borrador(
        bd, cid, tipo="seguimiento", asunto="nuevo", cuerpo_carta="c",
        ruta_pdf_hv="/tmp/n.pdf",
    )
    # Forzar fechas distintas (CURRENT_TIMESTAMP de SQLite puede empatar).
    conn = conectar(bd)
    try:
        conn.execute("UPDATE borradores SET fecha_creado = '2024-01-01 00:00:00' WHERE id = ?", (b_viejo,))
        conn.execute("UPDATE borradores SET fecha_creado = '2024-06-01 00:00:00' WHERE id = ?", (b_nuevo,))
        conn.commit()
    finally:
        conn.close()

    listos = borradores_listos_para_subir(bd)
    assert [b["id"] for b in listos] == [b_viejo, b_nuevo]


# ---------------------------------------------------------------------------
# marcar_borrador_subido
# ---------------------------------------------------------------------------

def test_marcar_borrador_subido_actualiza_estado_y_draft_id(tmp_path):
    bd = _bd(tmp_path)
    cid = _colegio_enriquecido(bd)
    bid = insertar_borrador(
        bd, cid, tipo="inicial", asunto="A", cuerpo_carta="c",
        ruta_pdf_hv="/tmp/a.pdf",
    )

    marcar_borrador_subido(bd, bid, gmail_draft_id="draft-xyz")

    conn = conectar(bd)
    try:
        row = conn.execute(
            "SELECT estado, gmail_draft_id, fecha_subido, error_mensaje FROM borradores WHERE id = ?",
            (bid,),
        ).fetchone()
    finally:
        conn.close()
    assert row["estado"] == "subido"
    assert row["gmail_draft_id"] == "draft-xyz"
    assert row["fecha_subido"] is not None
    assert row["error_mensaje"] is None


# ---------------------------------------------------------------------------
# marcar_borrador_fallo
# ---------------------------------------------------------------------------

def test_marcar_borrador_fallo_guarda_mensaje_y_estado(tmp_path):
    bd = _bd(tmp_path)
    cid = _colegio_enriquecido(bd)
    bid = insertar_borrador(
        bd, cid, tipo="inicial", asunto="A", cuerpo_carta="c",
        ruta_pdf_hv="/tmp/a.pdf",
    )

    marcar_borrador_fallo(bd, bid, error_mensaje="API 500 timeout")

    conn = conectar(bd)
    try:
        row = conn.execute(
            "SELECT estado, error_mensaje, gmail_draft_id, fecha_subido FROM borradores WHERE id = ?",
            (bid,),
        ).fetchone()
    finally:
        conn.close()
    assert row["estado"] == "fallo"
    assert row["error_mensaje"] == "API 500 timeout"
    assert row["gmail_draft_id"] is None
    assert row["fecha_subido"] is None
