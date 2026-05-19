"""Reproduce 1 intento del paso 'bullets EXP_1' para el colegio fallido id=1."""
import json
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

from modulos.cliente_claude import ClienteClaude
from modulos.generar import (
    RUTA_PLANTILLA, RUTA_POLISHED_PDF, RUTA_POLISHED_DOCX, RUTA_PROMPT_BULLETS,
    _extraer_cv_base, _texto_cv_completo, _nombres_permitidos,
    _mensaje_bullets, _llamar_claude,
)
from modulos.validador import detectar_alucinaciones

load_dotenv("config/.env")
api_key = os.getenv("ANTHROPIC_API_KEY")

con = sqlite3.connect("data/colegios.db")
con.row_factory = sqlite3.Row
fila = con.execute("""
    SELECT id, nombre, ciudad, perfil_pedagogico
    FROM colegios WHERE id = 1
""").fetchone()
colegio = dict(fila)
colegio["perfil_pedagogico"] = json.loads(colegio["perfil_pedagogico"])

cv_original = _texto_cv_completo(RUTA_POLISHED_PDF)
valores_base = _extraer_cv_base(RUTA_PLANTILLA, RUTA_POLISHED_DOCX)
permitidos = _nombres_permitidos(colegio)

print(f"Colegio: {colegio['nombre']}")
print(f"\nEXP_1_TITULO: {valores_base['EXP_1_TITULO']}")
print(f"\nEXP_1_BULLETS_ACTUALES (primeros 400 chars):")
print(valores_base['EXP_1_BULLETS'][:400])

cliente = ClienteClaude(api_key=api_key)
mensaje = _mensaje_bullets(
    valores_base["EXP_1_TITULO"],
    valores_base["EXP_1_BULLETS"],
    colegio["perfil_pedagogico"],
)

print(f"\n{'='*60}\n=== INTENTO 1/1 (bullets EXP_1) ===\n{'='*60}")
texto, costo = _llamar_claude(cliente, RUTA_PROMPT_BULLETS, mensaje)
print(f"Costo: ${costo:.4f}\n")
print("--- TEXTO GENERADO ---")
print(texto)
print("\n--- VALIDADOR ---")
flagged = detectar_alucinaciones(cv_original, texto, permitidos)
if not flagged:
    print("[OK] SIN alucinaciones - habria pasado.")
else:
    print(f"[X] {len(flagged)} hechos flagueados:")
    for h in sorted(flagged):
        print(f"   {h!r}")
