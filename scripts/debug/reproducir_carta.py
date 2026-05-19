"""Reproduce 3 intentos del paso 'carta' para el colegio fallido id=1.

La carta MENCIONA el nombre del colegio + ciudad — punto donde el validador
suele rechazar por nombres expandidos. Coste: ~$0.05.
"""
import json
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from modulos.cliente_claude import ClienteClaude
from modulos.generar import (
    RUTA_POLISHED_PDF, RUTA_PROMPT_CARTA,
    _texto_cv_completo, _nombres_permitidos,
    _mensaje_carta, _llamar_claude,
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
permitidos = _nombres_permitidos(colegio)
print(f"Colegio: {colegio['nombre']} | Ciudad: {colegio['ciudad']}")
print(f"permitidos: {sorted(permitidos)}\n")

# Resumen breve de Daniel (en producción se usa el PERFIL ya reescrito)
resumen_daniel = (
    "Daniel Eduardo Villalba de Oro es profesional en docencia e investigación, "
    "con experiencia en innovación educativa, uso de tecnologías digitales en el aula, "
    "y formación en educación física."
)

cliente = ClienteClaude(api_key=api_key)
mensaje = _mensaje_carta(
    colegio["nombre"], colegio["ciudad"], colegio["perfil_pedagogico"], resumen_daniel
)

for intento in range(1, 4):
    print(f"\n{'='*60}\n=== INTENTO {intento}/3 ===\n{'='*60}")
    texto, costo = _llamar_claude(cliente, RUTA_PROMPT_CARTA, mensaje)
    print(f"Costo: ${costo:.4f}\n")
    print("--- TEXTO GENERADO ---")
    print(texto)
    print("\n--- VALIDADOR ---")
    flagged = detectar_alucinaciones(cv_original, texto, permitidos)
    if not flagged:
        print("[OK] SIN alucinaciones - HABRIA pasado.")
    else:
        print(f"[X] {len(flagged)} hechos FLAGUEADOS:")
        for h in sorted(flagged):
            print(f"   {h!r}")
