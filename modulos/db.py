import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def conectar(ruta: Path | str) -> sqlite3.Connection:
    """Devuelve una conexión a la BD con foreign keys activadas."""
    conn = sqlite3.connect(str(ruta))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db(ruta: Path | str) -> None:
    """Crea la BD si no existe y aplica el schema (idempotente)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = conectar(ruta)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
