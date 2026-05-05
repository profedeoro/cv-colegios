import shutil
from pathlib import Path

RETENCION_DIAS = 7


def respaldar_bd(ruta_bd: Path | str) -> None:
    """Crea bak.1 (más reciente), rotando los anteriores. Borra los que excedan retención."""
    ruta_bd = Path(ruta_bd)
    if not ruta_bd.exists():
        return

    # Borrar el más viejo si excede retención
    viejo = ruta_bd.with_suffix(ruta_bd.suffix + f".bak.{RETENCION_DIAS}")
    if viejo.exists():
        viejo.unlink()

    # Rotar: bak.6 -> bak.7, bak.5 -> bak.6, ..., bak.1 -> bak.2
    for i in range(RETENCION_DIAS - 1, 0, -1):
        actual = ruta_bd.with_suffix(ruta_bd.suffix + f".bak.{i}")
        siguiente = ruta_bd.with_suffix(ruta_bd.suffix + f".bak.{i + 1}")
        if actual.exists():
            actual.rename(siguiente)

    # Crear bak.1 a partir del archivo actual
    bak1 = ruta_bd.with_suffix(ruta_bd.suffix + ".bak.1")
    shutil.copy2(ruta_bd, bak1)
