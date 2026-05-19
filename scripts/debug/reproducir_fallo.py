"""Reproduce UNA llamada al paso 'perfil' para un colegio fallido y muestra qué alucinó.

Cuesta ~$0.02. NO modifica la BD.
"""
import json
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from modulos.cliente_claude import ClienteClaude
from modulos.generar import (
    RUTA_PLANTILLA, RUTA_POLISHED_PDF, RUTA_POLISHED_DOCX, RUTA_PROMPT_PERFIL,
    _extraer_cv_base, _texto_cv_completo, _nombres_permitidos,
    _mensaje_perfil, _llamar_claude,
)
from modulos.validador import detectar_alucinaciones

# 1) Cargar API key
load_dotenv("config/.env")
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise SystemExit("Falta ANTHROPIC_API_KEY en config/.env")

# 2) Tomar el primer colegio en revisar_manualmente
BD = Path(__file__).parent / "data" / "colegios.db"
con = sqlite3.connect(BD)
con.row_factory = sqlite3.Row
fila = con.execute("""
    SELECT id, nombre, ciudad, perfil_pedagogico
    FROM colegios WHERE estado='revisar_manualmente'
    ORDER BY id LIMIT 1
""").fetchone()
if not fila:
    raise SystemExit("No hay colegios en revisar_manualmente.")
colegio = dict(fila)
colegio["perfil_pedagogico"] = json.loads(colegio["perfil_pedagogico"])
print(f"=== Reproduciendo paso 'perfil' para id={colegio['id']} '{colegio['nombre']}' ===\n")

# 3) Cargar inputs igual que lo hace generar.ejecutar
cv_original = _texto_cv_completo(RUTA_POLISHED_PDF)
valores_base = _extraer_cv_base(RUTA_PLANTILLA, RUTA_POLISHED_DOCX)
permitidos = _nombres_permitidos(colegio)
perfil_actual = valores_base["PERFIL"]
print(f"PERFIL_ACTUAL ({len(perfil_actual)} chars):")
print(perfil_actual[:300] + "...\n")

print(f"PERFIL_COLEGIO: {json.dumps(colegio['perfil_pedagogico'], ensure_ascii=False)}\n")
print(f"NOMBRE_COLEGIO: {colegio['nombre']}\n")
print(f"permitidos: {sorted(permitidos)}\n")

# 4) Llamar Claude UNA vez
cliente = ClienteClaude(api_key=api_key)
mensaje = _mensaje_perfil(perfil_actual, colegio["perfil_pedagogico"], colegio["nombre"])
print("=== Llamando Claude (sonnet-4-6)... ===")
texto, costo = _llamar_claude(cliente, RUTA_PROMPT_PERFIL, mensaje)
print(f"Costo: ${costo:.4f}\n")

print("=== TEXTO GENERADO POR CLAUDE ===")
print(texto)
print()

# 5) Validador
print("=== VALIDADOR ===")
flagged = detectar_alucinaciones(cv_original, texto, permitidos)
if not flagged:
    print("✅ SIN alucinaciones — este intento HABRÍA pasado.")
else:
    print(f"❌ {len(flagged)} hechos FLAGUEADOS como alucinación:")
    for h in sorted(flagged):
        print(f"   {h!r}")
    print()
    print("Cada uno de estos debe estar en cv_original (CV pulido) o en permitidos.")
    print("Si NO está, Claude lo inventó (o el validador es muy estricto).")
