"""Parser del CSV del directorio MEN.

Daniel descarga el CSV manualmente desde datos.gov.co y lo coloca en
data/raw/men_directorio.csv. Esta función lo parsea y filtra los colegios
no oficiales de Bogotá D.C., Antioquia, y Barranquilla (Atlántico).

El dataset oficial del MEN tiene SEDES (no establecimientos): cada colegio puede
aparecer varias veces (sede principal + rurales). Filtramos por PRINCIPAL='S'
para quedarnos solo con la sede principal de cada establecimiento.
"""
import csv
from pathlib import Path
from modulos.scrapers.tipos import ColegioInfo

# Departamentos completos: Bogotá y Antioquia (todo).
# Atlántico: solo Barranquilla.
# Las claves se comparan en MAYÚSCULAS contra el valor del CSV (también upper).
REGIONES_OBJETIVO = {
    "BOGOTÁ D.C.": None,
    "BOGOTA D.C.": None,
    "CAPITAL BOGOTÁ, D.C.": None,    # variante real del CSV oficial del MEN
    "CAPITAL BOGOTA, D.C.": None,    # sin acento
    "ANTIOQUIA": None,
    "ATLÁNTICO": {"BARRANQUILLA"},
    "ATLANTICO": {"BARRANQUILLA"},
}

# Mapeo flexible. Cada campo lógico tiene varios candidatos de columna.
COLUMNAS = {
    "nombre": ["NOMBRE_ESTABLECIMIENTO", "Nombre del Establecimiento", "ESTABLECIMIENTO", "NOMBRE"],
    "municipio": ["MUNICIPIO", "Municipio", "MUNICIPIO_NOMBRE"],
    "departamento": ["DEPARTAMENTO", "Departamento", "DEPARTAMENTO_NOMBRE"],
    "naturaleza": ["NATURALEZA", "Naturaleza", "SECTOR", "CTE_ID_SECTOR"],
}

# Columnas opcionales: si están, se usan; si no, se omiten.
COLUMNAS_OPCIONALES = {
    "nit": ["NIT", "Nit", "nit"],
    "principal": ["PRINCIPAL", "Principal", "ES_PRINCIPAL"],
}


def _detectar_columnas(headers: list[str]) -> dict[str, str]:
    """Mapea cada campo lógico al nombre de columna real del CSV.

    Para campos requeridos, lanza ValueError si no encuentra ninguno.
    Para opcionales, simplemente no aparecen en el dict si no están.
    """
    mapeo = {}
    for campo, candidatos in COLUMNAS.items():
        for c in candidatos:
            if c in headers:
                mapeo[campo] = c
                break
        else:
            raise ValueError(f"No encontré ninguna columna válida para '{campo}'. Probé: {candidatos}")
    for campo, candidatos in COLUMNAS_OPCIONALES.items():
        for c in candidatos:
            if c in headers:
                mapeo[campo] = c
                break
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
    """Parsea el CSV del MEN y devuelve los colegios no oficiales de las regiones objetivo.

    Si el CSV tiene columna PRINCIPAL, filtra solo PRINCIPAL='S' para evitar duplicados de sede.
    Si tiene columna NIT, la incluye; si no, deja nit=None.
    """
    ruta = Path(ruta_csv)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró {ruta}. Descárgalo de datos.gov.co.")

    colegios = []
    with ruta.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        col = _detectar_columnas(reader.fieldnames or [])
        col_principal = col.get("principal")
        col_nit = col.get("nit")
        for fila in reader:
            naturaleza = fila[col["naturaleza"]].strip().upper()
            if "NO OFICIAL" not in naturaleza and "PRIVAD" not in naturaleza:
                continue
            departamento = fila[col["departamento"]].strip()
            municipio = fila[col["municipio"]].strip()
            if not _es_region_objetivo(departamento, municipio):
                continue
            # Si hay columna PRINCIPAL, solo aceptar la sede principal
            if col_principal and fila[col_principal].strip().upper() != "S":
                continue
            colegios.append(ColegioInfo(
                nombre=fila[col["nombre"]].strip(),
                ciudad=municipio,
                departamento=departamento,
                fuente="MEN",
                nit=fila[col_nit].strip() if col_nit and fila[col_nit].strip() else None,
            ))
    return colegios
