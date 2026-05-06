"""Extracción de emails, selección de destinatario, validación MX."""
import re
import dns.resolver
import dns.exception

# Regex moderado: requiere TLD de al menos 2 letras (no captura "abc@def")
RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Prefijos en orden de preferencia (más arriba = más relevante para Daniel).
PREFIJOS_PREFERIDOS = [
    "rector",
    "direccion", "dirección",
    "recursos.humanos", "rrhh", "talento.humano",
    "talento",
    "secretaria.academica",
    "info", "informacion", "información",
    "contacto",
]


def extraer_emails(html: str) -> list[str]:
    """Extrae emails únicos (case-insensitive) del HTML."""
    encontrados = RE_EMAIL.findall(html)
    vistos = set()
    resultado = []
    for e in encontrados:
        e_low = e.lower()
        if e_low not in vistos:
            vistos.add(e_low)
            resultado.append(e_low)
    return resultado


def seleccionar_destinatario(emails: list[str]) -> str | None:
    """Aplica heurística de preferencia. Devuelve el mejor email o None."""
    if not emails:
        return None
    for prefijo in PREFIJOS_PREFERIDOS:
        for e in emails:
            local = e.split("@")[0]
            if local.lower() == prefijo:
                return e
    return min(emails, key=len)


def validar_dominio(email: str) -> bool:
    """True si el dominio del email tiene registros MX (DNS lookup)."""
    if "@" not in email:
        return False
    parts = email.split("@", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False
    dominio = parts[1]
    try:
        respuesta = dns.resolver.resolve(dominio, "MX", lifetime=5.0)
        return len(respuesta) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
            dns.resolver.NoNameservers, dns.exception.Timeout):
        return False
