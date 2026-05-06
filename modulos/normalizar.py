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
    """Normaliza un nombre de ciudad para almacenamiento y deduplicación uniforme.

    Ejemplos:
        "BOGOTÁ D.C." -> "Bogotá"
        "MEDELLÍN"    -> "Medellín"
        "Bogotá"      -> "Bogotá"
        "BARRANQUILLA"-> "Barranquilla"
    """
    if not ciudad:
        return ciudad
    # Toma solo la primera palabra (elimina sufijos como "D.C.")
    primera = re.split(r"[\s,.]", ciudad.strip())[0]
    if not primera:
        primera = ciudad.strip()
    # Convierte a título conservando los caracteres acentuados originales
    return primera.title()
