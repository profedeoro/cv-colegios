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


def test_extraer_emails_ignora_archivos_imagen():
    """Strings tipo 'logo@2x.png' o 'icon@3x.svg' NO son emails."""
    html = "<img src='bc-logo@3x.png'> <img src='icon@2x.svg'> info@real.com"
    emails = extraer_emails(html)
    assert "info@real.com" in emails
    assert "bc-logo@3x.png" not in emails
    assert "icon@2x.svg" not in emails


def test_extraer_emails_ignora_otros_archivos():
    html = "doc@manual.pdf style@theme.css script@app.js info@valido.edu.co"
    emails = extraer_emails(html)
    assert "info@valido.edu.co" in emails
    assert all("." not in e.split("@")[1] or e.split("@")[1].rsplit(".", 1)[1] not in {"pdf", "css", "js"} for e in emails)


def test_validar_dominio_rechaza_email_con_dominio_vacio():
    """Bug regresión: dominio con label vacío (e.g., 'algo@.com') no debe crashear."""
    assert validar_dominio("algo@.com") is False
    assert validar_dominio("algo@..") is False
    assert validar_dominio("algo@") is False


def test_validar_dominio_rechaza_emails_malformados_sin_crashear():
    """Garantiza que ninguna excepción de dnspython se propaga."""
    cases = [
        "test@invalid_chars!.com",
        "test@..com",
        "test@-leading-hyphen.com",
        "test@trailing-hyphen-.com",
    ]
    for caso in cases:
        # No debe crashear, debe retornar False
        result = validar_dominio(caso)
        assert result is False, f"Falló con '{caso}'"
