import sqlite3
import pytest

from modulos.db import (
    inicializar_db, insertar_colegio,
    marcar_enriquecido, marcar_sin_correo,
    colegios_para_generar, incrementar_intento_generar,
    insertar_borrador, marcar_borrador_creado,
    conectar, EstadoInvalidoError,
)


def _bd_inicial(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    return bd


def _enriquecer(bd, cid, correo="rector@x.edu.co"):
    marcar_enriquecido(
        bd, cid,
        web="https://x.edu.co",
        correo="info@x.edu.co",
        correo_destinatario=correo,
        perfil_pedagogico={"bilingue": True},
        palabras_clave=["IB"],
    )


def test_colegios_para_generar_solo_enriquecidos(tmp_path):
    bd = _bd_inicial(tmp_path)
    cid_desc = insertar_colegio(bd, nombre="Colegio Desc", ciudad="Bogotá",
                                departamento="Bogotá D.C.", fuente="MEN")
    cid_enr = insertar_colegio(bd, nombre="Colegio Enr", ciudad="Bogotá",
                               departamento="Bogotá D.C.", fuente="MEN")
    cid_sin = insertar_colegio(bd, nombre="Colegio Sin", ciudad="Bogotá",
                               departamento="Bogotá D.C.", fuente="MEN")
    _enriquecer(bd, cid_enr)
    marcar_sin_correo(bd, cid_sin, web="https://sin.edu.co")

    pendientes = colegios_para_generar(bd, limite=10)
    ids = [c["id"] for c in pendientes]
    assert ids == [cid_enr]
    assert pendientes[0]["estado"] == "enriquecido"


def test_colegios_para_generar_respeta_limite(tmp_path):
    bd = _bd_inicial(tmp_path)
    for i in range(5):
        cid = insertar_colegio(bd, nombre=f"Colegio Test {i}", ciudad="Bogotá",
                               departamento="Bogotá D.C.", fuente="MEN")
        _enriquecer(bd, cid)
    pendientes = colegios_para_generar(bd, limite=3)
    assert len(pendientes) == 3


def test_colegios_para_generar_excluye_con_3_intentos(tmp_path):
    bd = _bd_inicial(tmp_path)
    cid_a = insertar_colegio(bd, nombre="Colegio A", ciudad="Bogotá",
                             departamento="Bogotá D.C.", fuente="MEN")
    cid_b = insertar_colegio(bd, nombre="Colegio B", ciudad="Bogotá",
                             departamento="Bogotá D.C.", fuente="MEN")
    _enriquecer(bd, cid_a)
    _enriquecer(bd, cid_b)
    incrementar_intento_generar(bd, cid_a)
    incrementar_intento_generar(bd, cid_a)
    incrementar_intento_generar(bd, cid_a)

    pendientes = colegios_para_generar(bd, limite=10)
    ids = [c["id"] for c in pendientes]
    assert cid_a not in ids
    assert cid_b in ids


def test_colegios_para_generar_orden_por_fecha(tmp_path):
    bd = _bd_inicial(tmp_path)
    cid_viejo = insertar_colegio(bd, nombre="Colegio Viejo", ciudad="Bogotá",
                                 departamento="Bogotá D.C.", fuente="MEN")
    cid_nuevo = insertar_colegio(bd, nombre="Colegio Nuevo", ciudad="Bogotá",
                                 departamento="Bogotá D.C.", fuente="MEN")
    _enriquecer(bd, cid_viejo)
    _enriquecer(bd, cid_nuevo)
    # Forzar diferentes fechas via SQL directo (CURRENT_TIMESTAMP puede coincidir)
    conn = conectar(bd)
    try:
        conn.execute("UPDATE colegios SET fecha_enriquecido = '2024-01-01 00:00:00' WHERE id = ?", (cid_viejo,))
        conn.execute("UPDATE colegios SET fecha_enriquecido = '2024-06-01 00:00:00' WHERE id = ?", (cid_nuevo,))
        conn.commit()
    finally:
        conn.close()

    pendientes = colegios_para_generar(bd, limite=10)
    ids = [c["id"] for c in pendientes]
    assert ids == [cid_viejo, cid_nuevo]


def test_incrementar_intento_generar(tmp_path):
    bd = _bd_inicial(tmp_path)
    cid = insertar_colegio(bd, nombre="Colegio X", ciudad="Bogotá",
                           departamento="Bogotá D.C.", fuente="MEN")

    def _intentos():
        conn = conectar(bd)
        try:
            return conn.execute("SELECT intentos_generar FROM colegios WHERE id = ?", (cid,)).fetchone()[0]
        finally:
            conn.close()

    assert _intentos() == 0
    incrementar_intento_generar(bd, cid)
    assert _intentos() == 1
    incrementar_intento_generar(bd, cid)
    assert _intentos() == 2
    incrementar_intento_generar(bd, cid)
    assert _intentos() == 3


def test_insertar_borrador(tmp_path):
    bd = _bd_inicial(tmp_path)
    cid = insertar_colegio(bd, nombre="Colegio Y", ciudad="Bogotá",
                           departamento="Bogotá D.C.", fuente="MEN")
    bid = insertar_borrador(
        bd, cid,
        tipo="inicial",
        asunto="Postulación docente E.F.",
        cuerpo_carta="Estimado rector...",
        ruta_pdf_hv="/tmp/hv.pdf",
    )
    assert isinstance(bid, int) and bid > 0

    conn = conectar(bd)
    try:
        row = conn.execute("SELECT * FROM borradores WHERE id = ?", (bid,)).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row["colegio_id"] == cid
    assert row["tipo"] == "inicial"
    assert row["asunto"] == "Postulación docente E.F."
    assert row["cuerpo_carta"] == "Estimado rector..."
    assert row["ruta_pdf_hv"] == "/tmp/hv.pdf"
    assert row["estado"] == "listo_para_subir"


def test_insertar_borrador_tipo_invalido(tmp_path):
    bd = _bd_inicial(tmp_path)
    cid = insertar_colegio(bd, nombre="Colegio Z", ciudad="Bogotá",
                           departamento="Bogotá D.C.", fuente="MEN")
    with pytest.raises(sqlite3.IntegrityError):
        insertar_borrador(
            bd, cid,
            tipo="otro_valor",
            asunto="X",
            cuerpo_carta="Y",
            ruta_pdf_hv="/tmp/hv.pdf",
        )


def test_marcar_borrador_creado_cambia_estado_y_guarda_ids(tmp_path):
    bd = _bd_inicial(tmp_path)
    cid = insertar_colegio(bd, nombre="Colegio W", ciudad="Bogotá",
                           departamento="Bogotá D.C.", fuente="MEN")
    _enriquecer(bd, cid)
    marcar_borrador_creado(bd, cid, gmail_draft_id="d_123", gmail_thread_id="t_456")

    conn = conectar(bd)
    try:
        row = conn.execute(
            "SELECT estado, gmail_draft_id, gmail_thread_id FROM colegios WHERE id = ?",
            (cid,),
        ).fetchone()
    finally:
        conn.close()
    assert row["estado"] == "borrador_creado"
    assert row["gmail_draft_id"] == "d_123"
    assert row["gmail_thread_id"] == "t_456"


def test_marcar_borrador_creado_falla_desde_estado_invalido(tmp_path):
    bd = _bd_inicial(tmp_path)
    cid = insertar_colegio(bd, nombre="Colegio V", ciudad="Bogotá",
                           departamento="Bogotá D.C.", fuente="MEN")
    # estado actual: descubierto. No es transición válida → borrador_creado.
    with pytest.raises(EstadoInvalidoError):
        marcar_borrador_creado(bd, cid, gmail_draft_id="d_x", gmail_thread_id="t_x")
