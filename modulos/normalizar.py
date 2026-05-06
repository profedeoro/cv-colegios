import re
import unicodedata

SUFIJOS = {"sas", "sa", "ltda", "spa"}
PALABRAS_GENERICAS = {"colegio", "institucion", "corporacion", "gimnasio", "liceo", "escuela", "educativa", "instituto"}


def normalizar_nombre(nombre: str) -> str:
    """Normaliza un nombre de colegio para deduplicación."""
    sin_acentos = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii")
    sin_puntos = sin_acentos.replace(".", "").lower()
    palabras = re.findall(r"\w+", sin_puntos)
    filtradas = [p for p in palabras if p not in PALABRAS_GENERICAS and p not in SUFIJOS]
    return " ".join(filtradas)


def normalizar_ciudad(ciudad: str) -> str:
    """Normaliza un nombre de ciudad: title case + strip 'D.C.' suffix.

    Solo elimina el sufijo "D.C." (variantes con espacios/puntos/casing) que aparece
    en MEN para Bogotá. Preserva nombres multi-palabra como "El Carmen de Viboral".

    Ejemplos:
        "BOGOTÁ D.C." -> "Bogotá"
        "Bogotá D.C"  -> "Bogotá"
        "MEDELLÍN"    -> "Medellín"
        "El Carmen de Viboral" -> "El Carmen De Viboral"
        "BARRANQUILLA"-> "Barranquilla"
    """
    if not ciudad or not ciudad.strip():
        return ciudad
    # Strip D.C. suffix (Bogotá D.C. -> Bogotá). Acepta variantes de espacios y puntos.
    limpia = re.sub(r"\s+D\.?\s*C\.?\s*$", "", ciudad.strip(), flags=re.IGNORECASE)
    return limpia.title()
