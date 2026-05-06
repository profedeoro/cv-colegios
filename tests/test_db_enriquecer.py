import json
from modulos.db import (
    inicializar_db, insertar_colegio,
    colegios_para_enriquecer, marcar_enriquecido, marcar_sin_correo, incrementar_intento_enriquecer,
    conectar,
)


def _bd_con_colegios(tmp_path, n=5):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    for i in range(n):
        insertar_colegio(bd, nombre=f"Colegio Test {i}", ciudad="Bogotá",
                         departamento="Bogotá D.C.", fuente="MEN")
    return bd


def test_colegios_para_enriquecer_devuelve_solo_descubiertos(tmp_path):
    bd = _bd_con_colegios(tmp_path, n=5)
    pendientes = colegios_para_enriquecer(bd, limite=10)
    assert len(pendientes) == 5
    assert all(c["estado"] == "descubierto" for c in pendientes)


def test_colegios_para_enriquecer_respeta_limite(tmp_path):
    bd = _bd_con_colegios(tmp_path, n=10)
    pendientes = colegios_para_enriquecer(bd, limite=3)
    assert len(pendientes) == 3


def test_colegios_para_enriquecer_excluye_con_3_intentos(tmp_path):
    bd = _bd_con_colegios(tmp_path, n=2)
    cid = colegios_para_enriquecer(bd, limite=10)[0]["id"]
    incrementar_intento_enriquecer(bd, cid)
    incrementar_intento_enriquecer(bd, cid)
    incrementar_intento_enriquecer(bd, cid)
    pendientes = colegios_para_enriquecer(bd, limite=10)
    ids = [c["id"] for c in pendientes]
    assert cid not in ids


def test_marcar_enriquecido_actualiza_campos(tmp_path):
    bd = _bd_con_colegios(tmp_path, n=1)
    cid = colegios_para_enriquecer(bd, limite=1)[0]["id"]
    marcar_enriquecido(bd, cid,
                       web="https://x.edu.co",
                       correo="info@x.edu.co",
                       correo_destinatario="rector@x.edu.co",
                       perfil_pedagogico={"bilingue": True},
                       palabras_clave=["IB", "innovación"])
    conn = conectar(bd)
    row = conn.execute("SELECT * FROM colegios WHERE id = ?", (cid,)).fetchone()
    conn.close()
    assert row["estado"] == "enriquecido"
    assert row["web"] == "https://x.edu.co"
    assert row["correo"] == "info@x.edu.co"
    assert row["correo_destinatario"] == "rector@x.edu.co"
    assert json.loads(row["perfil_pedagogico"])["bilingue"] is True
    assert json.loads(row["palabras_clave"]) == ["IB", "innovación"]
    assert row["fecha_enriquecido"] is not None


def test_marcar_sin_correo_cambia_estado(tmp_path):
    bd = _bd_con_colegios(tmp_path, n=1)
    cid = colegios_para_enriquecer(bd, limite=1)[0]["id"]
    marcar_sin_correo(bd, cid, web="https://x.edu.co")
    conn = conectar(bd)
    row = conn.execute("SELECT estado, web FROM colegios WHERE id = ?", (cid,)).fetchone()
    conn.close()
    assert row["estado"] == "sin_correo"
    assert row["web"] == "https://x.edu.co"
