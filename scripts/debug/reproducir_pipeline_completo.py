"""Reproduce el pipeline COMPLETO (perfil + bullets + carta) para colegio id=1.

Usa el PERFIL reescrito por Claude como RESUMEN_DANIEL para la carta — igual
que el orquestador real. Muestra qué hechos se flaguean en cada paso.
"""
import json
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

from modulos.cliente_claude import ClienteClaude
from modulos.generar import (
    RUTA_PLANTILLA, RUTA_POLISHED_PDF, RUTA_POLISHED_DOCX,
    RUTA_PROMPT_PERFIL, RUTA_PROMPT_CARTA,
    _extraer_cv_base, _texto_cv_completo, _nombres_permitidos,
    _mensaje_perfil, _mensaje_carta, _llamar_claude,
    _normalizar_nombre_colegio,
)
from modulos.validador import detectar_alucinaciones

load_dotenv("config/.env")
api_key = os.getenv("ANTHROPIC_API_KEY")

con = sqlite3.connect("data/colegios.db")
con.row_factory = sqlite3.Row
fila = con.execute("SELECT * FROM colegios WHERE id = 1").fetchone()
colegio = dict(fila)
colegio["perfil_pedagogico"] = json.loads(colegio["perfil_pedagogico"])

cv_original = _texto_cv_completo(RUTA_POLISHED_PDF)
valores_base = _extraer_cv_base(RUTA_PLANTILLA, RUTA_POLISHED_DOCX)
permitidos = _nombres_permitidos(colegio)
nombre_norm = _normalizar_nombre_colegio(colegio["nombre"])
ciudad = (colegio["ciudad"] or "").rstrip(",.")

print(f"Colegio: {colegio['nombre']} -> normalizado: {nombre_norm}")
print(f"Ciudad normalizada: {ciudad}")
print(f"permitidos: {sorted(permitidos)}\n")

cliente = ClienteClaude(api_key=api_key)

# === PASO 1: PERFIL ===
print(f"{'='*60}\n=== PASO 1: PERFIL ===\n{'='*60}")
mensaje_p = _mensaje_perfil(valores_base["PERFIL"], colegio["perfil_pedagogico"], nombre_norm)
texto_perfil, costo_p = _llamar_claude(cliente, RUTA_PROMPT_PERFIL, mensaje_p)
print(f"Costo: ${costo_p:.4f}")
print(f"\n--- PERFIL REESCRITO ---\n{texto_perfil}\n")
flagged_p = detectar_alucinaciones(cv_original, texto_perfil, permitidos)
if flagged_p:
    print(f"[X] PERFIL flaguea: {sorted(flagged_p)}")
else:
    print("[OK] PERFIL pasa.")

# === PASO 3: CARTA (con el perfil de arriba como resumen) ===
print(f"\n{'='*60}\n=== PASO 3: CARTA (resumen = perfil reescrito) ===\n{'='*60}")
mensaje_c = _mensaje_carta(nombre_norm, ciudad, colegio["perfil_pedagogico"], texto_perfil)
texto_carta, costo_c = _llamar_claude(cliente, RUTA_PROMPT_CARTA, mensaje_c)
print(f"Costo: ${costo_c:.4f}")
print(f"\n--- CARTA ---\n{texto_carta}\n")
flagged_c = detectar_alucinaciones(cv_original, texto_carta, permitidos)
if flagged_c:
    print(f"[X] CARTA flaguea {len(flagged_c)} hechos: {sorted(flagged_c)}")
else:
    print("[OK] CARTA pasa.")

print(f"\nCosto total: ${costo_p+costo_c:.4f}")
