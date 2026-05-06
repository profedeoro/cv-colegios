"""Orquestador del módulo enriquecer.

Para cada colegio en estado 'descubierto':
1. Encontrar su web (si no la tiene) usando Brave Search.
2. Bajar el HTML de la home.
3. Extraer emails y elegir destinatario por heurística.
4. Validar dominio del correo (MX lookup).
5. Clasificar perfil pedagógico con Claude.
6. Marcar como 'enriquecido' o 'sin_correo' o 'error' según resultado.
"""
import time
from pathlib import Path
from selectolax.parser import HTMLParser

from modulos.db import (
    colegios_para_enriquecer,
    marcar_enriquecido,
    marcar_sin_correo,
    incrementar_intento_enriquecer,
    registrar_ejecucion,
)
from modulos.email_extractor import extraer_emails, seleccionar_destinatario, validar_dominio
from modulos.http_cliente import fetch_html, HttpError
from modulos.logger import obtener_logger
from modulos.web_finder import encontrar_web
from modulos.clasificador_pedagogico import clasificar


def _texto_visible(html: str) -> str:
    """Extrae texto visible del HTML (sin tags, scripts, estilos). Limita a 10000 chars."""
    tree = HTMLParser(html)
    for nodo in tree.css("script, style, noscript"):
        nodo.decompose()
    texto = tree.body.text(separator=" ", strip=True) if tree.body else ""
    return texto[:10000]


def procesar_colegio(ruta_bd, colegio: dict, cliente_claude, brave_api_key: str) -> dict:
    """Procesa un colegio completo. Devuelve dict con resumen del resultado."""
    log = obtener_logger("enriquecer")
    cid = colegio["id"]
    nombre = colegio["nombre"]
    web_existente = colegio.get("web")

    web = web_existente
    if not web:
        try:
            web = encontrar_web(nombre, colegio["ciudad"], api_key=brave_api_key)
        except Exception as e:
            log.warning(f"[{cid}] Error buscando web de '{nombre}': {e}")
            web = None

    if not web:
        log.info(f"[{cid}] Sin web encontrada para '{nombre}'")
        marcar_sin_correo(ruta_bd, cid, web=None)
        return {"colegio_id": cid, "estado_final": "sin_correo", "razon": "no_web"}

    try:
        html = fetch_html(web)
    except HttpError as e:
        log.warning(f"[{cid}] Falló descarga de {web}: {e}")
        incrementar_intento_enriquecer(ruta_bd, cid)
        return {"colegio_id": cid, "estado_final": "error", "razon": str(e)}

    emails = extraer_emails(html)
    destinatario = seleccionar_destinatario(emails)
    if not destinatario:
        log.info(f"[{cid}] Web encontrada ({web}) pero sin emails")
        marcar_sin_correo(ruta_bd, cid, web=web)
        return {"colegio_id": cid, "estado_final": "sin_correo", "razon": "sin_email"}

    if not validar_dominio(destinatario):
        log.info(f"[{cid}] Email {destinatario} con dominio inválido")
        marcar_sin_correo(ruta_bd, cid, web=web)
        return {"colegio_id": cid, "estado_final": "sin_correo", "razon": "dominio_invalido"}

    texto = _texto_visible(html)
    try:
        perfil, costo = clasificar(texto, cliente_claude)
    except (ValueError, KeyError) as e:
        log.warning(f"[{cid}] Clasificación falló: {e}")
        incrementar_intento_enriquecer(ruta_bd, cid)
        return {"colegio_id": cid, "estado_final": "error", "razon": f"clasificacion: {e}"}

    palabras_clave = perfil.pop("palabras_clave", [])
    marcar_enriquecido(
        ruta_bd, cid,
        web=web,
        correo=emails[0] if emails else None,
        correo_destinatario=destinatario,
        perfil_pedagogico=perfil,
        palabras_clave=palabras_clave,
    )
    log.info(f"[{cid}] Enriquecido: {nombre} ({destinatario})")
    return {"colegio_id": cid, "estado_final": "enriquecido", "costo": costo}


def ejecutar(
    ruta_bd: Path,
    cliente_claude,
    brave_api_key: str,
    max_colegios: int = 30,
) -> dict:
    """Procesa hasta max_colegios pendientes y devuelve resumen."""
    log = obtener_logger("enriquecer")
    log.info(f"Iniciando enriquecimiento (max={max_colegios})")
    inicio = time.monotonic()

    pendientes = colegios_para_enriquecer(ruta_bd, limite=max_colegios)
    log.info(f"Pendientes encontrados: {len(pendientes)}")

    resumen = {"enriquecido": 0, "sin_correo": 0, "error": 0}
    costo_total = 0.0
    for col in pendientes:
        resultado = procesar_colegio(ruta_bd, col, cliente_claude, brave_api_key)
        resumen[resultado["estado_final"]] = resumen.get(resultado["estado_final"], 0) + 1
        costo_total += resultado.get("costo", 0)

    duracion = time.monotonic() - inicio
    estado = "ok" if resumen["error"] < len(pendientes) else "error"
    registrar_ejecucion(
        ruta_bd, modulo="enriquecer", duracion_segundos=duracion,
        estado=estado, colegios_procesados=len(pendientes),
        costo_api_usd=costo_total,
    )
    log.info(f"Enriquecimiento terminado en {duracion:.1f}s. Resumen: {resumen}. Costo: ${costo_total:.4f}")
    return {"resumen": resumen, "costo_usd": costo_total, "duracion_seg": duracion}
