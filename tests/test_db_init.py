import sqlite3
import pytest
from pathlib import Path
from modulos.db import inicializar_db, conectar, _migrar_correo_invalido_si_falta


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


def test_constraint_estado_acepta_correo_invalido(tmp_path):
    """El CHECK del esquema vigente debe admitir 'correo_invalido'."""
    ruta = tmp_path / "test.db"
    inicializar_db(ruta)
    conn = conectar(ruta)
    # No debe lanzar IntegrityError.
    conn.execute(
        "INSERT INTO colegios "
        "(nombre, nombre_normalizado, ciudad, departamento, fuente, estado) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("Y", "y", "Bogotá", "Bogotá D.C.", "MEN", "correo_invalido"),
    )
    conn.commit()
    row = conn.execute("SELECT estado FROM colegios WHERE nombre = 'Y'").fetchone()
    conn.close()
    assert row["estado"] == "correo_invalido"


# ---------------------------------------------------------------------------
# Migración idempotente: BD vieja sin 'correo_invalido' en el CHECK
# ---------------------------------------------------------------------------

# Schema viejo (snapshot literal del CHECK previo a esta migración). Sirve
# para simular una BD creada con una versión anterior y verificar que
# `_migrar_correo_invalido_si_falta` la actualiza preservando los datos.
_SCHEMA_VIEJO_COLEGIOS = """
CREATE TABLE colegios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    nombre_normalizado TEXT NOT NULL,
    ciudad TEXT NOT NULL,
    departamento TEXT NOT NULL,
    nit TEXT,
    web TEXT,
    correo TEXT,
    correo_destinatario TEXT,
    fuente TEXT NOT NULL,
    perfil_pedagogico TEXT,
    palabras_clave TEXT,
    estado TEXT NOT NULL DEFAULT 'descubierto',
    intentos_enriquecer INTEGER NOT NULL DEFAULT 0,
    intentos_generar INTEGER NOT NULL DEFAULT 0,
    fecha_descubierto DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_enriquecido DATETIME,
    fecha_envio DATETIME,
    fecha_respuesta DATETIME,
    gmail_draft_id TEXT,
    gmail_thread_id TEXT,
    notas TEXT,
    CHECK (estado IN (
        'descubierto', 'enriquecido', 'sin_correo', 'borrador_creado',
        'enviado', 'respondió', 'rebotó', 'seguimiento_pendiente',
        'sin_respuesta', 'descartado', 'error', 'revisar_manualmente'
    ))
);
CREATE UNIQUE INDEX ix_colegios_dedup ON colegios(nombre_normalizado, ciudad);
CREATE UNIQUE INDEX ix_colegios_nit ON colegios(nit) WHERE nit IS NOT NULL;
CREATE INDEX ix_colegios_estado ON colegios(estado);
CREATE INDEX ix_colegios_thread ON colegios(gmail_thread_id);
"""


def _crear_bd_vieja(ruta: Path) -> None:
    conn = sqlite3.connect(str(ruta))
    conn.executescript(_SCHEMA_VIEJO_COLEGIOS)
    conn.commit()
    conn.close()


def test_migracion_correo_invalido_en_bd_vieja(tmp_path):
    """BD creada con schema viejo → al inicializar, el CHECK se actualiza."""
    ruta = tmp_path / "viejo.db"
    _crear_bd_vieja(ruta)

    # Insertar filas de datos reales para asegurar que sobreviven.
    conn = sqlite3.connect(str(ruta))
    conn.executemany(
        "INSERT INTO colegios (nombre, nombre_normalizado, ciudad, departamento, "
        "fuente, estado) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("Colegio A", "colegio a", "Bogotá", "Bogotá D.C.", "MEN", "descubierto"),
            ("Colegio B", "colegio b", "Medellín", "Antioquia", "MEN", "enriquecido"),
            ("Colegio C", "colegio c", "Cali", "Valle", "MEN", "borrador_creado"),
        ],
    )
    conn.commit()
    # Confirmar que el CHECK viejo rechaza 'correo_invalido'.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO colegios (nombre, nombre_normalizado, ciudad, departamento, "
            "fuente, estado) VALUES (?, ?, ?, ?, ?, ?)",
            ("Z", "z", "X", "Y", "M", "correo_invalido"),
        )
    conn.rollback()
    filas_antes = conn.execute("SELECT COUNT(*) FROM colegios").fetchone()[0]
    conn.close()
    assert filas_antes == 3

    # Inicializar (debe disparar la migración).
    inicializar_db(ruta)

    # Verificar: filas preservadas, ahora el CHECK admite 'correo_invalido'.
    conn = conectar(ruta)
    filas_despues = conn.execute("SELECT COUNT(*) FROM colegios").fetchone()[0]
    conn.execute(
        "INSERT INTO colegios (nombre, nombre_normalizado, ciudad, departamento, "
        "fuente, estado) VALUES (?, ?, ?, ?, ?, ?)",
        ("Colegio CI", "colegio ci", "Pasto", "Nariño", "MEN", "correo_invalido"),
    )
    conn.commit()
    estados = [
        r["estado"]
        for r in conn.execute(
            "SELECT estado FROM colegios ORDER BY id"
        ).fetchall()
    ]
    # Índices únicos siguen vigentes.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO colegios (nombre, nombre_normalizado, ciudad, departamento, "
            "fuente, estado) VALUES (?, ?, ?, ?, ?, ?)",
            ("Colegio A2", "colegio a", "Bogotá", "Bogotá D.C.", "MEN", "descubierto"),
        )
    conn.rollback()
    conn.close()

    assert filas_despues == 3
    assert estados == ["descubierto", "enriquecido", "borrador_creado", "correo_invalido"]


def test_migracion_correo_invalido_es_idempotente(tmp_path):
    """Ejecutar la migración dos veces sobre la misma BD → segunda es no-op."""
    ruta = tmp_path / "idem.db"
    _crear_bd_vieja(ruta)

    primera = _migrar_correo_invalido_si_falta(ruta)
    segunda = _migrar_correo_invalido_si_falta(ruta)
    tercera = _migrar_correo_invalido_si_falta(ruta)

    assert primera is True   # primera vez migra
    assert segunda is False  # ya migrado
    assert tercera is False


def test_migracion_correo_invalido_noop_en_bd_nueva(tmp_path):
    """BD creada con schema vigente → la migración es no-op."""
    ruta = tmp_path / "nueva.db"
    inicializar_db(ruta)
    # Ejecutar el helper directamente: debe devolver False.
    assert _migrar_correo_invalido_si_falta(ruta) is False


def test_migracion_correo_invalido_noop_en_bd_inexistente(tmp_path):
    """Si la tabla `colegios` no existe (BD vacía recién creada sin schema)
    el helper devuelve False sin error."""
    ruta = tmp_path / "vacia.db"
    # Crear archivo sqlite vacío (sin schema).
    sqlite3.connect(str(ruta)).close()
    assert _migrar_correo_invalido_si_falta(ruta) is False
