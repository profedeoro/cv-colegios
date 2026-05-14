"""Cliente Gmail OAuth: carga el token, refresca si toca, crea borradores."""
from __future__ import annotations

import base64
import mimetypes
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# Scope mínimo para crear borradores en la cuenta de Daniel.
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def obtener_servicio_gmail(
    ruta_credenciales: str = "config/credentials.json",
    ruta_token: str = "config/gmail_token.json",
):
    """Devuelve un service de Gmail listo para usar.

    Lee el token previamente guardado por `autorizar_gmail.py`. Si está expirado
    pero hay refresh_token, lo refresca y reescribe el archivo en disco.

    Raises:
        FileNotFoundError: si el token no existe todavía.
    """
    ruta_token_p = Path(ruta_token)
    if not ruta_token_p.exists():
        raise FileNotFoundError(
            f"No se encontró {ruta_token_p}. "
            "Ejecuta `python autorizar_gmail.py` primero para autorizar la cuenta."
        )

    creds = Credentials.from_authorized_user_file(str(ruta_token_p), SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            ruta_token_p.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError(
                f"Las credenciales en {ruta_token_p} no son válidas y no se pueden refrescar. "
                "Borra el archivo y vuelve a ejecutar `python autorizar_gmail.py`."
            )

    return build("gmail", "v1", credentials=creds)


def crear_borrador(
    service,
    destinatario: str,
    asunto: str,
    cuerpo: str,
    adjunto_pdf: str | None = None,
) -> tuple[str, str]:
    """Crea un borrador en Gmail (no lo envía). Devuelve (draft_id, thread_id).

    Si `adjunto_pdf` se entrega y el archivo no existe, lanza FileNotFoundError
    antes de tocar el API (fail-fast).
    """
    mensaje = EmailMessage()
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    # Cuerpo plano UTF-8. Gmail rellena el From con el usuario autenticado.
    mensaje.set_content(cuerpo, subtype="plain", charset="utf-8")

    if adjunto_pdf is not None:
        ruta_pdf = Path(adjunto_pdf)
        if not ruta_pdf.is_file():
            raise FileNotFoundError(
                f"No se encontró el adjunto PDF: {ruta_pdf}"
            )
        datos = ruta_pdf.read_bytes()
        tipo, _ = mimetypes.guess_type(ruta_pdf.name)
        if tipo is None:
            tipo = "application/pdf"
        maintype, _, subtype = tipo.partition("/")
        mensaje.add_attachment(
            datos,
            maintype=maintype or "application",
            subtype=subtype or "pdf",
            filename=ruta_pdf.name,
        )

    raw = base64.urlsafe_b64encode(bytes(mensaje)).decode("ascii")

    respuesta = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw}})
        .execute()
    )

    draft_id = respuesta["id"]
    thread_id = respuesta["message"]["threadId"]
    return draft_id, thread_id
