"""Parser del CSV del directorio MEN.

Daniel descarga el CSV manualmente desde datos.gov.co y lo coloca en
data/raw/men_directorio.csv. Esta función lo parsea y filtra los colegios
no oficiales de Bogotá D.C., Antioquia, y Barranquilla (Atlántico).
"""
import csv
from pathlib import Path
from modulos.scrapers.tipos import ColegioInfo

# Departamentos completos: Bogotá y Antioquia (todo).
# Atlántico: solo Barranquilla.
REGIONES_OBJETIVO = {
    "BOGOTÁ D.C.": None,        # None = todos los municipios
    "BOGOTA D.C.": None,        # variante sin acento
    "ANTIOQUIA": None,
    "ATLÁNTICO": {"BARRANQUILLA"},
    "ATLANTICO": {"BARRANQUILLA"},
}

# Si el CSV usa otros nombres de columna, ajustar este mapeo:
COLUMNAS = {
    "nit": ["NIT", "Nit", "nit"],
    "nombre": ["NOMBRE_ESTABLECIMIENTO", "Nombre del Establecimiento", "ESTABLECIMIENTO", "NOMBRE"],
    "municipio": ["MUNICIPIO", "Municipio", "MUNICIPIO_NOMBRE"],
    "departamento": ["DEPARTAMENTO", "Departamento", "DEPARTAMENTO_NOMBRE"],
    "naturaleza": ["NATURALEZA", "Naturaleza", "SECTOR"],
}


def _detectar_columnas(headers: list[str]) -> dict[str, str]:
    """Mapea cada campo lógico al nombre de columna real del CSV."""
    mapeo = {}
    for campo, candidatos in COLUMNAS.items():
        for c in candidatos:
            if c in headers:
                mapeo[campo] = c
                break
        else:
            raise ValueError(f"No encontré ninguna columna válida para '{campo}'. Probé: {candidatos}")
    return mapeo


def _es_region_objetivo(departamento: str, municipio: str) -> bool:
    dep = departamento.strip().upper()
    mun = municipio.strip().upper()
    if dep not in REGIONES_OBJETIVO:
        return False
    municipios_permitidos = REGIONES_OBJETIVO[dep]
    if municipios_permitidos is None:
        return True
    return mun in municipios_permitidos


def parsear_men(ruta_csv: Path | str) -> list[ColegioInfo]:
    """Parsea el CSV del MEN y devuelve los colegios no oficiales de las regiones objetivo."""
    ruta = Path(ruta_csv)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró {ruta}. Descárgalo de datos.gov.co.")

    colegios = []
    with ruta.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        col = _detectar_columnas(reader.fieldnames or [])
        for fila in reader:
            naturaleza = fila[col["naturaleza"]].strip().upper()
            if "NO OFICIAL" not in naturaleza and "PRIVAD" not in naturaleza:
                continue
            departamento = fila[col["departamento"]].strip()
            municipio = fila[col["municipio"]].strip()
            if not _es_region_objetivo(departamento, municipio):
                continue
            colegios.append(ColegioInfo(
                nombre=fila[col["nombre"]].strip(),
                ciudad=municipio,
                departamento=departamento,
                fuente="MEN",
                nit=fila[col["nit"]].strip() or None,
            ))
    return colegios
