"""Orquestador del módulo `enviar_borradores`.

Para cada fila en `borradores` con estado `listo_para_subir`:
1. Obtiene el `service` de Gmail (con refresh automático del token).
2. Llama a `crear_borrador` con destinatario/asunto/cuerpo/PDF adjunto.
3. En caso de éxito:
   - Marca el borrador como `subido` con el `gmail_draft_id`.
   - Transiciona el colegio a `borrador_creado` y guarda los ids de Gmail.
4. En caso de error:
   - HttpError con señal clara de "correo inválido" (HTTP 400 +
     mensaje del API) → marca el borrador como `fallo`, transiciona el
     colegio al estado terminal `correo_invalido` y lo cuenta aparte en
     el resumen. El `error_mensaje` queda guardado en la fila del
     borrador para trazabilidad. `correo_invalido` es terminal: no hay
     transiciones de salida, así que Daniel debe corregir el correo
     manualmente si quiere reintentar.
   - Otros HttpError / excepciones inesperadas → marca el borrador como
     `fallo`, no toca el colegio (Daniel puede reintentar).
5. Al final registra una fila en `registro_ejecuciones`.

Mockea `obtener_servicio_gmail` y `crear_borrador` desde este módulo en los
tests; ambas son importadas localmente para que `patch.object` funcione.
"""
from __future__ import annotations

import time
from typing import Any

from googleapiclient.errors import HttpError

from modulos.db import (
    borradores_listos_para_subir,
    cambiar_estado,
    marcar_borrador_creado,
    marcar_borrador_fallo,
    marcar_borrador_subido,
    registrar_ejecucion,
)
from modulos.gmail_oauth import crear_borrador, obtener_servicio_gmail
from modulos.logger import obtener_logger


# Frases que el API de Gmail incluye cuando la dirección destinatario es inválida.
# Cubre "Invalid 'to' header" / "Invalid To header" en distintas capitalizaciones.
_PATRONES_CORREO_INVALIDO = (
    "invalid 'to' header",
    "invalid to header",
    "invalid email",
    "address does not exist",
    "invalid recipient",
)


def _es_correo_invalido(err: HttpError) -> bool:
    """Heurística para distinguir correo inválido de otros errores del API.

    Gmail devuelve HTTP 400 con un mensaje claro cuando rechaza la dirección
    destinatario. Usamos un substring check sobre la representación textual
    del error (que incluye el body JSON crudo) para evitar parsear el JSON
    manualmente — los SDK de Google ya hacen un best-effort por incluir el
    `message` en `str(err)`.

    Sólo devolvemos True si:
    - El status es 400 (Bad Request), y
    - El texto del error contiene alguno de los patrones reconocidos.
    """
    status = getattr(getattr(err, "resp", None), "status", None)
    if status != 400:
        return False
    texto = str(err).lower()
    return any(p in texto for p in _PATRONES_CORREO_INVALIDO)


def ejecutar(ruta_bd, ruta_token: str = "config/gmail_token.json") -> dict:
    """Procesa todos los borradores en estado `listo_para_subir`.

    Args:
        ruta_bd: Ruta al archivo SQLite.
        ruta_token: Ruta al token OAuth de Gmail.

    Returns:
        Dict con el resumen:
            {"total": N, "subidos": k, "fallos": j, "correo_invalido": m}
        donde N == k + j + m.
    """
    log = obtener_logger("enviar_borradores")
    log.info("Iniciando envío de borradores a Gmail (modo: crear borradores, no enviar)")
    inicio = time.monotonic()

    service: Any = obtener_servicio_gmail(ruta_token)
    pendientes = borradores_listos_para_subir(ruta_bd)
    log.info(f"Borradores listos para subir: {len(pendientes)}")

    resumen = {
        "total": len(pendientes),
        "subidos": 0,
        "fallos": 0,
        "correo_invalido": 0,
    }

    for b in pendientes:
        bid = b["id"]
        cid = b["colegio_id"]
        destinatario = b["correo_destinatario"]
        try:
            draft_id, thread_id = crear_borrador(
                service,
                destinatario=destinatario,
                asunto=b["asunto"],
                cuerpo=b["cuerpo_carta"],
                adjunto_pdf=b["ruta_pdf_hv"],
            )
            # Primero marcar el borrador como subido (no toca colegio); luego
            # validar y aplicar la transición de colegio. Si la transición
            # fallara (p. ej. el colegio ya no está en 'enriquecido'), el
            # except inferior la convierte en fallo del borrador. Como ya
            # marcamos 'subido' arriba, hacemos rollback explícito para
            # mantener consistencia.
            marcar_borrador_subido(ruta_bd, bid, draft_id)
            try:
                marcar_borrador_creado(ruta_bd, cid, draft_id, thread_id)
            except Exception as e:
                # El draft sí se creó en Gmail, pero no podemos transicionar el
                # colegio. Revertimos el borrador a 'fallo' para que el
                # operador investigue (probablemente el colegio cambió de
                # estado en otra ejecución).
                log.exception(
                    f"[borrador {bid}] draft creado en Gmail pero falló "
                    f"marcar_borrador_creado(colegio={cid}): {e}"
                )
                marcar_borrador_fallo(
                    ruta_bd, bid,
                    f"draft creado ({draft_id}) pero transición colegio falló: {e}",
                )
                resumen["fallos"] += 1
                continue

            resumen["subidos"] += 1
            log.info(f"[borrador {bid}] subido como draft '{draft_id}' (colegio {cid})")

        except HttpError as e:
            if _es_correo_invalido(e):
                log.warning(
                    f"[borrador {bid}] correo inválido rechazado por Gmail "
                    f"(destinatario={destinatario!r}): {e}"
                )
                marcar_borrador_fallo(
                    ruta_bd, bid, f"correo inválido: {e}",
                )
                # Transicionar el colegio al estado terminal correo_invalido.
                # Si la transición falla (p. ej. el colegio ya no está en
                # un estado del que se pueda llegar a correo_invalido), lo
                # registramos pero NO escalamos a fallo genérico: el
                # correo sí es inválido y eso es lo que el contador refleja.
                try:
                    cambiar_estado(ruta_bd, cid, "correo_invalido")
                except Exception as e2:
                    log.warning(
                        f"[borrador {bid}] no se pudo transicionar colegio "
                        f"{cid} a 'correo_invalido': {e2}"
                    )
                resumen["correo_invalido"] += 1
            else:
                log.exception(f"[borrador {bid}] HttpError de Gmail: {e}")
                marcar_borrador_fallo(ruta_bd, bid, f"HttpError: {e}")
                resumen["fallos"] += 1

        except Exception as e:
            log.exception(f"[borrador {bid}] error inesperado: {e}")
            marcar_borrador_fallo(ruta_bd, bid, str(e))
            resumen["fallos"] += 1

    duracion = time.monotonic() - inicio
    estado_ejec = "ok" if resumen["fallos"] == 0 else "error"
    mensaje = (
        f"subidos={resumen['subidos']} "
        f"correo_invalido={resumen['correo_invalido']} "
        f"fallos={resumen['fallos']}"
    )
    registrar_ejecucion(
        ruta_bd,
        modulo="enviar_borradores",
        duracion_segundos=duracion,
        estado=estado_ejec,
        colegios_procesados=resumen["total"],
        mensaje=mensaje,
    )
    log.info(f"Envío terminado en {duracion:.1f}s. Resumen: {resumen}")
    return resumen
