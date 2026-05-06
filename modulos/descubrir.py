"""Orquestador del módulo `descubrir`.

Llama a las 5 fuentes (MEN, UNCOLI, CONACED, ASCOLPEM, Google CSE),
inserta en BD con dedup, y registra la ejecución.
"""
import json
import time
from pathlib import Path
from modulos.db import insertar_colegio, registrar_ejecucion, contar_colegios
from modulos.logger import obtener_logger
from modulos.normalizar import normalizar_ciudad
from modulos.scrapers.men import parsear_men
from modulos.scrapers.uncoli import scrape_uncoli
from modulos.scrapers.conaced import scrape_conaced
from modulos.scrapers.ascolpem import scrape_ascolpem
from modulos.scrapers.google_cse import queries_a_colegios
from modulos.scrapers.tipos import ColegioInfo


def _insertar_lote(ruta_bd, lote: list[ColegioInfo], log) -> int:
    """Inserta cada colegio (con dedup automática). Devuelve cuántos NUEVOS se crearon."""
    antes = contar_colegios(ruta_bd)
    procesados_con_error = 0
    for col in lote:
        try:
            insertar_colegio(
                ruta_bd,
                nombre=col.nombre,
                ciudad=normalizar_ciudad(col.ciudad),
                departamento=col.departamento,
                fuente=col.fuente,
                nit=col.nit,
                web=col.web,
            )
        except ValueError as e:
            log.warning(f"Saltando colegio inválido: {col.nombre} ({e})")
            procesados_con_error += 1
    nuevos = contar_colegios(ruta_bd) - antes
    if procesados_con_error:
        log.info(f"Lote: {len(lote)} recibidos, {nuevos} nuevos, {procesados_con_error} con error.")
    return nuevos


def ejecutar(
    ruta_bd: Path,
    ruta_csv_men: Path | None = None,
    queries_path: Path | None = None,
    google_api_key: str | None = None,
    google_engine_id: str | None = None,
) -> dict:
    """Corre las 5 fuentes en orden y devuelve un resumen."""
    log = obtener_logger("descubrir")
    inicio = time.monotonic()
    resumen = {"MEN": 0, "UNCOLI": 0, "CONACED": 0, "ASCOLPEM": 0, "Google": 0}
    errores = []

    # 1. MEN
    if ruta_csv_men and Path(ruta_csv_men).exists():
        try:
            log.info(f"Leyendo MEN desde {ruta_csv_men}")
            colegios = parsear_men(ruta_csv_men)
            log.info(f"MEN: {len(colegios)} colegios candidatos")
            resumen["MEN"] = _insertar_lote(ruta_bd, colegios, log)
        except Exception as e:
            log.error(f"MEN falló: {e}")
            errores.append(f"MEN: {e}")
    else:
        log.warning("CSV del MEN no encontrado, se omite esta fuente.")

    # 2. UNCOLI
    try:
        log.info("Scrapeando UNCOLI...")
        resumen["UNCOLI"] = _insertar_lote(ruta_bd, scrape_uncoli(), log)
    except Exception as e:
        log.error(f"UNCOLI falló: {e}")
        errores.append(f"UNCOLI: {e}")

    # 3. CONACED
    try:
        log.info("Scrapeando CONACED...")
        resumen["CONACED"] = _insertar_lote(ruta_bd, scrape_conaced(), log)
    except Exception as e:
        log.error(f"CONACED falló: {e}")
        errores.append(f"CONACED: {e}")

    # 4. ASCOLPEM
    try:
        log.info("Scrapeando ASCOLPEM...")
        resumen["ASCOLPEM"] = _insertar_lote(ruta_bd, scrape_ascolpem(), log)
    except Exception as e:
        log.error(f"ASCOLPEM falló: {e}")
        errores.append(f"ASCOLPEM: {e}")

    # 5. Google CSE
    if queries_path and Path(queries_path).exists() and google_api_key and google_engine_id:
        try:
            log.info(f"Cargando queries de {queries_path}")
            queries = json.loads(Path(queries_path).read_text(encoding="utf-8"))["queries"]
            colegios = queries_a_colegios(queries, google_api_key, google_engine_id)
            log.info(f"Google CSE: {len(colegios)} resultados")
            resumen["Google"] = _insertar_lote(ruta_bd, colegios, log)
        except Exception as e:
            log.error(f"Google CSE falló: {e}")
            errores.append(f"Google: {e}")
    else:
        log.warning("Google CSE no configurado, se omite esta fuente.")

    duracion = time.monotonic() - inicio
    estado = "ok" if not errores else "error"
    mensaje = "; ".join(errores) if errores else None
    total = sum(resumen.values())

    registrar_ejecucion(
        ruta_bd,
        modulo="descubrir",
        duracion_segundos=duracion,
        estado=estado,
        colegios_procesados=total,
        mensaje=mensaje,
    )

    log.info(f"Descubrimiento terminado en {duracion:.1f}s. Resumen: {resumen}")
    return resumen
