import pytest
from modulos.email_extractor import (
    extraer_emails,
    seleccionar_destinatario,
    validar_dominio,
)


def test_extraer_emails_simple():
    html = "<html>contacto@colegio.edu.co y rector@colegio.edu.co</html>"
    emails = extraer_emails(html)
    assert "contacto@colegio.edu.co" in emails
    assert "rector@colegio.edu.co" in emails


def test_extraer_emails_quita_duplicados():
    html = "info@x.co info@x.co INFO@x.co"
    emails = extraer_emails(html)
    assert emails.count("info@x.co") == 1


def test_extraer_emails_descarta_basura():
    html = "abc@def, foo@bar.x, valido@col.edu.co"
    emails = extraer_emails(html)
    assert "valido@col.edu.co" in emails
    assert "abc@def" not in emails


def test_seleccionar_prefiere_rector():
    emails = ["info@x.co", "rector@x.co", "contacto@x.co"]
    assert seleccionar_destinatario(emails) == "rector@x.co"


def test_seleccionar_prefiere_direccion_si_no_rector():
    emails = ["info@x.co", "direccion@x.co", "contacto@x.co"]
    assert seleccionar_destinatario(emails) == "direccion@x.co"


def test_seleccionar_jerarquia_completa():
    pares = [
        (["talento@x.co", "info@x.co"], "talento@x.co"),
        (["info@x.co", "contacto@x.co"], "info@x.co"),
        (["recursos.humanos@x.co", "info@x.co"], "recursos.humanos@x.co"),
    ]
    for emails, esperado in pares:
        assert seleccionar_destinatario(emails) == esperado


def test_seleccionar_devuelve_none_lista_vacia():
    assert seleccionar_destinatario([]) is None


def test_seleccionar_fallback_al_mas_corto_si_ninguno_encaja():
    emails = ["administracion@x.co", "abc@x.co"]
    assert seleccionar_destinatario(emails) == "abc@x.co"


def test_validar_dominio_acepta_dominio_valido():
    """Test con dominio real (gmail.com tiene MX)."""
    assert validar_dominio("test@gmail.com") is True


def test_validar_dominio_rechaza_dominio_inexistente():
    assert validar_dominio("test@este-dominio-no-existe-12345xyz.tld") is False


def test_validar_dominio_rechaza_email_malformado():
    assert validar_dominio("notanemail") is False
    assert validar_dominio("@x.co") is False
    assert validar_dominio("x@") is False
