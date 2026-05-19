"""Diagnóstico rápido del estado de la BD."""
import sqlite3
from pathlib import Path

BD = Path(__file__).parent / "data" / "colegios.db"
con = sqlite3.connect(BD)
con.row_factory = sqlite3.Row

print("\n=== Estados de COLEGIOS ===")
for r in con.execute("SELECT estado, COUNT(*) FROM colegios GROUP BY estado ORDER BY 2 DESC"):
    print(f"  {r[0]:30s} {r[1]}")

print("\n=== Estados de BORRADORES ===")
total = con.execute("SELECT COUNT(*) FROM borradores").fetchone()[0]
print(f"  Total filas: {total}")
for r in con.execute("SELECT estado, COUNT(*) FROM borradores GROUP BY estado"):
    print(f"  {r[0]:30s} {r[1]}")

print("\n=== Últimas 5 ejecuciones registradas ===")
sql_ejec = "SELECT modulo, estado, fecha, duracion_segundos, mensaje, costo_api_usd FROM registro_ejecuciones ORDER BY id DESC LIMIT 5"
for r in con.execute(sql_ejec):
    print(f"  [{r['fecha']}] {r['modulo']:20s} estado={r['estado']:6s} dur={r['duracion_segundos'] or 0:.1f}s costo=${r['costo_api_usd']:.4f}")
    print(f"      msg: {r['mensaje']}")

print("\n=== Colegios en revisar_manualmente (los que el validador rechazó 3x) ===")
sql_rev = """
    SELECT id, nombre, ciudad, departamento, correo_destinatario, intentos_generar
    FROM colegios
    WHERE estado = 'revisar_manualmente'
    ORDER BY id LIMIT 5
"""
for r in con.execute(sql_rev):
    print(f"  id={r['id']:5d} intentos={r['intentos_generar']} {r['nombre'][:60]}")
    print(f"        ciudad={r['ciudad']}, correo={r['correo_destinatario']}")
