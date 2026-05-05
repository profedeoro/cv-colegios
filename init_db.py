"""Comando único: crea data/colegios.db si no existe."""
from pathlib import Path
from modulos.db import inicializar_db

RUTA_BD = Path(__file__).parent / "data" / "colegios.db"


def main():
    inicializar_db(RUTA_BD)
    print(f"Base de datos lista en {RUTA_BD.resolve()}")


if __name__ == "__main__":
    main()
