"""Tipos compartidos entre scrapers."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ColegioInfo:
    """Información mínima de un colegio descubierto por una fuente.

    Solo contiene lo que las fuentes pueden saber con certeza. El enriquecimiento
    (web, correo, perfil pedagógico) se hace en una fase posterior (Plan 3).
    """
    nombre: str
    ciudad: str
    departamento: str
    fuente: str                     # "MEN", "UNCOLI", "CONACED", "ASCOLPEM", "Google"
    nit: str | None = None          # solo lo tienen MEN; otras fuentes no
    web: str | None = None          # algunas fuentes lo saben (UNCOLI, Google)
