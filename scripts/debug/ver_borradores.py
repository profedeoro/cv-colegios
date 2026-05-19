"""Imprime los borradores pendientes para revisión rápida antes de subir a Gmail."""
import sqlite3
from pathlib import Path

BD = Path(__file__).parent / "data" / "colegios.db"

con = sqlite3.connect(BD)
con.row_factory = sqlite3.Row

sql = """
    SELECT b.id, c.nombre, c.correo_destinatario, b.asunto, b.cuerpo_carta, b.ruta_pdf_hv
    FROM borradores b
    JOIN colegios c ON c.id = b.colegio_id
    WHERE b.estado = 'listo_para_subir'
    ORDER BY b.id
"""

filas = list(con.execute(sql))
print(f"\n=== {len(filas)} borradores listos para subir ===\n")

for r in filas:
    print(f"--- Borrador #{r['id']} ---")
    print(f"Colegio:      {r['nombre']}")
    print(f"Destinatario: {r['correo_destinatario']}")
    print(f"Asunto:       {r['asunto']}")
    print(f"PDF:          {r['ruta_pdf_hv']}")
    print(f"\nCarta (primeros 400 chars):")
    print(r['cuerpo_carta'][:400])
    print(f"\n...[carta total: {len(r['cuerpo_carta'])} caracteres]\n")
    print("=" * 60 + "\n")
