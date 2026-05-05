import sqlite3
import pytest
from pathlib import Path
from modulos.db import inicializar_db, conectar


def test_inicializar_crea_tablas(tmp_path):
    ruta = tmp_path / "test.db"
    inicializar_db(ruta)
    conn = conectar(ruta)
    tablas = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "colegios" in tablas
    assert "borradores" in tablas
    assert "registro_ejecuciones" in tablas


def test_inicializar_es_idempotente(tmp_path):
    ruta = tmp_path / "test.db"
    inicializar_db(ruta)
    inicializar_db(ruta)  # No debe fallar
    conn = conectar(ruta)
    count = conn.execute("SELECT COUNT(*) FROM colegios").fetchone()[0]
    conn.close()
    assert count == 0


def test_constraint_estado_invalido(tmp_path):
    ruta = tmp_path / "test.db"
    inicializar_db(ruta)
    conn = conectar(ruta)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO colegios "
            "(nombre, nombre_normalizado, ciudad, departamento, fuente, estado) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("X", "x", "Bogotá", "Bogotá D.C.", "MEN", "estado_inventado"),
        )
    conn.close()
