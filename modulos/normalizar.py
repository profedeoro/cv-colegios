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
