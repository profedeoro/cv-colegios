"""Tests para modulos.gmail_oauth (con mocks de la API de Google)."""
import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modulos.gmail_oauth import crear_borrador, obtener_servicio_gmail


def _decodificar_raw(raw_b64: str) -> bytes:
    """Decodifica el campo 'raw' base64url devuelto al API de Gmail."""
    # Padding hasta múltiplo de 4
    pad = "=" * (-len(raw_b64) % 4)
    return base64.urlsafe_b64decode(raw_b64 + pad)


# ---------------------------------------------------------------------------
# obtener_servicio_gmail
# ---------------------------------------------------------------------------

def test_obtener_servicio_falla_si_no_existe_token(tmp_path):
    ruta_token = tmp_path / "gmail_token.json"
    with pytest.raises(FileNotFoundError, match="autorizar_gmail"):
        obtener_servicio_gmail(ruta_token=str(ruta_token))


def test_obtener_servicio_con_token_valido_devuelve_service(tmp_path):
    ruta_token = tmp_path / "gmail_token.json"
    ruta_token.write_text("{}", encoding="utf-8")  # contenido irrelevante: mockeamos el loader

    creds_mock = MagicMock()
    creds_mock.valid = True
    creds_mock.expired = False

    service_mock = MagicMock(name="gmail_service")

    with patch("modulos.gmail_oauth.Credentials") as mock_creds_cls, \
         patch("modulos.gmail_oauth.build") as mock_build:
        mock_creds_cls.from_authorized_user_file.return_value = creds_mock
        mock_build.return_value = service_mock

        service = obtener_servicio_gmail(ruta_token=str(ruta_token))

        assert service is service_mock
        mock_creds_cls.from_authorized_user_file.assert_called_once()
        mock_build.assert_called_once_with("gmail", "v1", credentials=creds_mock)
        # Token válido: no debe refrescarse.
        creds_mock.refresh.assert_not_called()


def test_obtener_servicio_refresca_token_expirado_y_guarda(tmp_path):
    ruta_token = tmp_path / "gmail_token.json"
    ruta_token.write_text('{"viejo": true}', encoding="utf-8")

    creds_mock = MagicMock()
    creds_mock.valid = False
    creds_mock.expired = True
    creds_mock.refresh_token = "refresh-xyz"
    creds_mock.to_json.return_value = '{"refrescado": true}'

    service_mock = MagicMock(name="gmail_service")

    with patch("modulos.gmail_oauth.Credentials") as mock_creds_cls, \
         patch("modulos.gmail_oauth.Request") as mock_request_cls, \
         patch("modulos.gmail_oauth.build") as mock_build:
        mock_creds_cls.from_authorized_user_file.return_value = creds_mock
        request_instancia = MagicMock(name="request_instance")
        mock_request_cls.return_value = request_instancia
        mock_build.return_value = service_mock

        service = obtener_servicio_gmail(ruta_token=str(ruta_token))

        assert service is service_mock
        creds_mock.refresh.assert_called_once_with(request_instancia)
        # El token en disco se reescribe con el JSON refrescado.
        contenido = ruta_token.read_text(encoding="utf-8")
        assert json.loads(contenido) == {"refrescado": True}


# ---------------------------------------------------------------------------
# crear_borrador
# ---------------------------------------------------------------------------

def test_crear_borrador_sin_adjunto_envia_mime_y_devuelve_ids():
    service = MagicMock(name="service")
    drafts = service.users.return_value.drafts.return_value
    drafts.create.return_value.execute.return_value = {
        "id": "r-abc",
        "message": {"id": "m-1", "threadId": "t-2"},
    }

    draft_id, thread_id = crear_borrador(
        service,
        destinatario="colegio@example.com",
        asunto="Hoja de vida — Daniel Villalba",
        cuerpo="Hola, adjunto mi hoja de vida.",
        adjunto_pdf=None,
    )

    assert draft_id == "r-abc"
    assert thread_id == "t-2"

    # Inspeccionar el cuerpo enviado al API.
    _, kwargs = drafts.create.call_args
    assert kwargs["userId"] == "me"
    raw_b64 = kwargs["body"]["message"]["raw"]
    mime_bytes = _decodificar_raw(raw_b64)
    mime_text = mime_bytes.decode("utf-8", errors="replace")

    assert "To: colegio@example.com" in mime_text
    # El asunto puede aparecer codificado (RFC2047) si contiene no-ASCII.
    assert "Subject:" in mime_text
    assert "Daniel Villalba" in mime_text or "=?utf-8?" in mime_text
    assert "Hola, adjunto mi hoja de vida." in mime_text


def test_crear_borrador_con_adjunto_pdf_incluye_archivo(tmp_path):
    pdf = tmp_path / "hoja_de_vida.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake pdf bytes")

    service = MagicMock(name="service")
    drafts = service.users.return_value.drafts.return_value
    drafts.create.return_value.execute.return_value = {
        "id": "r-zzz",
        "message": {"id": "m-9", "threadId": "t-9"},
    }

    draft_id, thread_id = crear_borrador(
        service,
        destinatario="rector@colegio.edu.co",
        asunto="Aplicación docente E.F.",
        cuerpo="Buen día, adjunto mi HV.",
        adjunto_pdf=str(pdf),
    )

    assert draft_id == "r-zzz"
    assert thread_id == "t-9"

    _, kwargs = drafts.create.call_args
    raw_b64 = kwargs["body"]["message"]["raw"]
    mime_bytes = _decodificar_raw(raw_b64)
    mime_text = mime_bytes.decode("utf-8", errors="replace")

    assert "hoja_de_vida.pdf" in mime_text
    assert "application/pdf" in mime_text
    # Es multipart.
    assert "multipart/" in mime_text.lower() or "Content-Type: multipart" in mime_text


def test_crear_borrador_con_adjunto_inexistente_falla(tmp_path):
    service = MagicMock(name="service")
    ruta_inexistente = tmp_path / "no_existe.pdf"

    with pytest.raises(FileNotFoundError):
        crear_borrador(
            service,
            destinatario="x@y.com",
            asunto="x",
            cuerpo="x",
            adjunto_pdf=str(ruta_inexistente),
        )
    # No debe haber llamado al API.
    service.users.return_value.drafts.return_value.create.assert_not_called()
