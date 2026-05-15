"""Reset de los colegios en revisar_manualmente para reintentarlos con el fix del validador."""
import sqlite3
from pathlib import Path

BD = Path(__file__).parent / "data" / "colegios.db"
con = sqlite3.connect(BD)
cur = con.execute("""
    UPDATE colegios
    SET estado = 'enriquecido', intentos_generar = 0
    WHERE estado = 'revisar_manualmente'
""")
print(f"Colegios reseteados: {cur.rowcount}")
con.commit()
