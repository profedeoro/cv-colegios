from modulos.db import inicializar_db, registrar_ejecucion, ultima_ejecucion_ok


def test_registrar_ejecucion_ok(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    registrar_ejecucion(bd, modulo="descubrir", duracion_segundos=12.5,
                        estado="ok", colegios_procesados=42, costo_api_usd=0.05)
    from modulos.db import conectar
    conn = conectar(bd)
    row = conn.execute("SELECT * FROM registro_ejecuciones").fetchone()
    conn.close()
    assert row["modulo"] == "descubrir"
    assert row["estado"] == "ok"
    assert row["colegios_procesados"] == 42


def test_ultima_ejecucion_ok_devuelve_fecha_si_existe(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    registrar_ejecucion(bd, modulo="descubrir", duracion_segundos=1.0, estado="ok")
    fecha = ultima_ejecucion_ok(bd, modulo="descubrir")
    assert fecha is not None


def test_ultima_ejecucion_ok_devuelve_none_si_no_existe(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    fecha = ultima_ejecucion_ok(bd, modulo="enriquecer")
    assert fecha is None


def test_ultima_ejecucion_ignora_errores(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    registrar_ejecucion(bd, modulo="x", duracion_segundos=1.0, estado="error", mensaje="boom")
    assert ultima_ejecucion_ok(bd, modulo="x") is None
