import sqlite3
from pathlib import Path

from modulos.normalizar import normalizar_nombre

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


def insertar_colegio(
    ruta_bd,
    *,
    nombre: str,
    ciudad: str,
    departamento: str,
    fuente: str,
    nit: str | None = None,
    web: str | None = None,
    correo: str | None = None,
) -> int:
    """Inserta un colegio. Si ya existe (por NIT o nombre+ciudad), acumula fuente. Devuelve id."""
    nombre_norm = normalizar_nombre(nombre)
    if not nombre_norm:
        raise ValueError(
            f"El nombre '{nombre}' se normaliza a cadena vacía (solo contiene palabras genéricas o sufijos legales). "
            "Agrega palabras distintivas al nombre antes de insertar."
        )
    conn = conectar(ruta_bd)
    try:
        # Buscar duplicado
        row = None
        if nit:
            row = conn.execute("SELECT id, fuente FROM colegios WHERE nit = ?", (nit,)).fetchone()
        if not row:
            row = conn.execute(
                "SELECT id, fuente FROM colegios WHERE nombre_normalizado = ? AND ciudad = ?",
                (nombre_norm, ciudad),
            ).fetchone()

        if row:
            fuentes = set(row["fuente"].split(","))
            fuentes.add(fuente)
            nueva = ",".join(sorted(fuentes))
            conn.execute("UPDATE colegios SET fuente = ? WHERE id = ?", (nueva, row["id"]))
            # Completar campos vacíos sin sobrescribir
            for campo, valor in [("nit", nit), ("web", web), ("correo", correo)]:
                if valor:
                    conn.execute(
                        f"UPDATE colegios SET {campo} = COALESCE({campo}, ?) WHERE id = ?",
                        (valor, row["id"]),
                    )
            conn.commit()
            return row["id"]

        cur = conn.execute(
            """INSERT INTO colegios (nombre, nombre_normalizado, ciudad, departamento,
                                      nit, web, correo, fuente)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (nombre, nombre_norm, ciudad, departamento, nit, web, correo, fuente),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def contar_colegios(ruta_bd) -> int:
    conn = conectar(ruta_bd)
    try:
        return conn.execute("SELECT COUNT(*) FROM colegios").fetchone()[0]
    finally:
        conn.close()


class EstadoInvalidoError(Exception):
    pass


TRANSICIONES_VALIDAS = {
    "descubierto": {"enriquecido", "sin_correo", "error", "descartado", "revisar_manualmente"},
    "enriquecido": {"borrador_creado", "descartado", "revisar_manualmente"},
    "sin_correo": {"enriquecido", "descartado"},
    "borrador_creado": {"enviado", "rebotó", "descartado"},
    "enviado": {"respondió", "seguimiento_pendiente", "rebotó", "descartado"},
    "seguimiento_pendiente": {"respondió", "sin_respuesta", "descartado"},
    "respondió": {"descartado"},
    "rebotó": {"descartado"},
    "sin_respuesta": {"descartado"},
    "descartado": set(),
    "error": {"descubierto", "descartado"},
    "revisar_manualmente": {"enriquecido", "descartado"},
}

ESTADOS_VALIDOS = set(TRANSICIONES_VALIDAS.keys())


def obtener_estado(ruta_bd, colegio_id: int) -> str:
    conn = conectar(ruta_bd)
    try:
        row = conn.execute("SELECT estado FROM colegios WHERE id = ?", (colegio_id,)).fetchone()
        if not row:
            raise EstadoInvalidoError(f"colegio id={colegio_id} no existe")
        return row["estado"]
    finally:
        conn.close()


def cambiar_estado(ruta_bd, colegio_id: int, nuevo_estado: str) -> None:
    if nuevo_estado not in ESTADOS_VALIDOS:
        raise EstadoInvalidoError(f"estado desconocido: {nuevo_estado}")
    actual = obtener_estado(ruta_bd, colegio_id)
    if nuevo_estado not in TRANSICIONES_VALIDAS[actual]:
        raise EstadoInvalidoError(
            f"no se puede pasar de {actual} a {nuevo_estado}"
        )
    conn = conectar(ruta_bd)
    try:
        conn.execute("UPDATE colegios SET estado = ? WHERE id = ?", (nuevo_estado, colegio_id))
        conn.commit()
    finally:
        conn.close()


def guardar_hash_cv(ruta_bd, hash_valor: str) -> None:
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            """INSERT INTO metadatos (clave, valor) VALUES ('hash_cv', ?)
               ON CONFLICT(clave) DO UPDATE
               SET valor = excluded.valor, fecha_actualizacion = CURRENT_TIMESTAMP""",
            (hash_valor,),
        )
        conn.commit()
    finally:
        conn.close()


def hash_cv_actual(ruta_bd) -> str | None:
    conn = conectar(ruta_bd)
    try:
        row = conn.execute("SELECT valor FROM metadatos WHERE clave = 'hash_cv'").fetchone()
        return row["valor"] if row else None
    finally:
        conn.close()


def registrar_ejecucion(
    ruta_bd,
    *,
    modulo: str,
    duracion_segundos: float,
    estado: str,
    colegios_procesados: int = 0,
    mensaje: str | None = None,
    costo_api_usd: float = 0.0,
) -> None:
    """Inserta una fila en registro_ejecuciones."""
    if estado not in ("ok", "error"):
        raise ValueError(f"estado inválido: {estado}")
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            """INSERT INTO registro_ejecuciones
               (modulo, duracion_segundos, estado, colegios_procesados, mensaje, costo_api_usd)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (modulo, duracion_segundos, estado, colegios_procesados, mensaje, costo_api_usd),
        )
        conn.commit()
    finally:
        conn.close()


def ultima_ejecucion_ok(ruta_bd, modulo: str) -> str | None:
    """Devuelve la fecha (ISO string) de la última ejecución 'ok' del módulo, o None."""
    conn = conectar(ruta_bd)
    try:
        row = conn.execute(
            """SELECT fecha FROM registro_ejecuciones
               WHERE modulo = ? AND estado = 'ok'
               ORDER BY fecha DESC LIMIT 1""",
            (modulo,),
        ).fetchone()
        return row["fecha"] if row else None
    finally:
        conn.close()


import json as _json


def colegios_para_enriquecer(ruta_bd, limite: int = 30) -> list[dict]:
    """Devuelve colegios en estado 'descubierto' con < 3 intentos, ordenados por fecha_descubierto."""
    conn = conectar(ruta_bd)
    try:
        rows = conn.execute(
            """SELECT * FROM colegios
               WHERE estado = 'descubierto' AND intentos_enriquecer < 3
               ORDER BY fecha_descubierto ASC
               LIMIT ?""",
            (limite,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def marcar_enriquecido(
    ruta_bd, colegio_id: int,
    *, web: str | None, correo: str | None, correo_destinatario: str | None,
    perfil_pedagogico: dict, palabras_clave: list[str],
) -> None:
    """Marca un colegio como enriquecido y actualiza sus datos."""
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            """UPDATE colegios SET
                 estado = 'enriquecido',
                 web = COALESCE(web, ?),
                 correo = ?,
                 correo_destinatario = ?,
                 perfil_pedagogico = ?,
                 palabras_clave = ?,
                 fecha_enriquecido = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (web, correo, correo_destinatario,
             _json.dumps(perfil_pedagogico, ensure_ascii=False),
             _json.dumps(palabras_clave, ensure_ascii=False),
             colegio_id),
        )
        conn.commit()
    finally:
        conn.close()


def marcar_sin_correo(ruta_bd, colegio_id: int, *, web: str | None = None) -> None:
    """Marca un colegio como sin_correo (web encontrada pero no email válido)."""
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            """UPDATE colegios SET estado = 'sin_correo',
                                    web = COALESCE(web, ?),
                                    fecha_enriquecido = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (web, colegio_id),
        )
        conn.commit()
    finally:
        conn.close()


def incrementar_intento_enriquecer(ruta_bd, colegio_id: int) -> None:
    """Incrementa contador de intentos. Si llega a 3, el colegio queda fuera del próximo lote."""
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            "UPDATE colegios SET intentos_enriquecer = intentos_enriquecer + 1 WHERE id = ?",
            (colegio_id,),
        )
        conn.commit()
    finally:
        conn.close()


def colegios_para_generar(ruta_bd, limite: int = 15) -> list[dict]:
    """Devuelve colegios en estado 'enriquecido' con < 3 intentos de generar, ordenados por fecha_enriquecido."""
    conn = conectar(ruta_bd)
    try:
        rows = conn.execute(
            """SELECT * FROM colegios
               WHERE estado = 'enriquecido' AND intentos_generar < 3
               ORDER BY fecha_enriquecido ASC
               LIMIT ?""",
            (limite,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def incrementar_intento_generar(ruta_bd, colegio_id: int) -> None:
    """Incrementa contador de intentos de generar. Si llega a 3, el colegio queda fuera del próximo lote."""
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            "UPDATE colegios SET intentos_generar = intentos_generar + 1 WHERE id = ?",
            (colegio_id,),
        )
        conn.commit()
    finally:
        conn.close()


def insertar_borrador(
    ruta_bd,
    colegio_id: int,
    *,
    tipo: str,
    asunto: str,
    cuerpo_carta: str,
    ruta_pdf_hv: str,
) -> int:
    """Inserta una fila en borradores. `tipo` debe ser 'inicial' o 'seguimiento'. Devuelve el id."""
    conn = conectar(ruta_bd)
    try:
        cur = conn.execute(
            """INSERT INTO borradores (colegio_id, tipo, asunto, cuerpo_carta, ruta_pdf_hv)
               VALUES (?, ?, ?, ?, ?)""",
            (colegio_id, tipo, asunto, cuerpo_carta, ruta_pdf_hv),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def marcar_borrador_creado(
    ruta_bd, colegio_id: int, gmail_draft_id: str, gmail_thread_id: str
) -> None:
    """Marca un colegio como borrador_creado y guarda los ids de Gmail.

    Usa cambiar_estado para validar la transición enriquecido → borrador_creado, luego
    persiste los identificadores de Gmail con un UPDATE adicional.
    """
    cambiar_estado(ruta_bd, colegio_id, "borrador_creado")
    conn = conectar(ruta_bd)
    try:
        conn.execute(
            "UPDATE colegios SET gmail_draft_id = ?, gmail_thread_id = ? WHERE id = ?",
            (gmail_draft_id, gmail_thread_id, colegio_id),
        )
        conn.commit()
    finally:
        conn.close()
