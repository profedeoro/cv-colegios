"""Extracción de emails, selección de destinatario, validación MX."""
import re
import dns.resolver
import dns.exception

# Regex moderado: requiere TLD de al menos 2 letras (no captura "abc@def")
RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

EXTENSIONES_ARCHIVO = {
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "bmp", "tiff",
    "css", "js", "html", "htm", "xml", "json",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "zip", "tar", "gz", "rar",
    "mp4", "mp3", "wav", "avi", "mov",
    "ttf", "woff", "woff2", "eot",
}

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


def _es_archivo_imagen(email: str) -> bool:
    """True si el 'email' es en realidad un nombre de archivo (logo@2x.png, etc.)."""
    if "@" not in email:
        return False
    parte_dominio = email.split("@", 1)[1]
    if "." not in parte_dominio:
        return False
    extension = parte_dominio.rsplit(".", 1)[1].lower()
    return extension in EXTENSIONES_ARCHIVO


def extraer_emails(html: str) -> list[str]:
    """Extrae emails únicos (case-insensitive) del HTML, excluyendo nombres de archivo."""
    encontrados = RE_EMAIL.findall(html)
    vistos = set()
    resultado = []
    for e in encontrados:
        e_low = e.lower()
        if e_low in vistos:
            continue
        if _es_archivo_imagen(e_low):
            continue
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
