"""Inspecciona los inputs que ve el validador anti-alucinación para un colegio fallido.

No llama a Claude. Solo dumpea qué información tiene el orquestador antes de generar.
Si los inputs están vacíos/rotos, el validador rechazará TODO lo que Claude genere.
"""
import json
import sqlite3
from pathlib import Path

from modulos.generar import (
    RUTA_PLANTILLA, RUTA_POLISHED_PDF, RUTA_POLISHED_DOCX,
    _extraer_cv_base, _texto_cv_completo, _nombres_permitidos,
)
from modulos.validador import extraer_hechos

BD = Path(__file__).parent / "data" / "colegios.db"
con = sqlite3.connect(BD)
con.row_factory = sqlite3.Row

# Tomar el primer colegio en revisar_manualmente
fila = con.execute("""
    SELECT id, nombre, ciudad, departamento, correo_destinatario, perfil_pedagogico
    FROM colegios
    WHERE estado = 'revisar_manualmente'
    ORDER BY id LIMIT 1
""").fetchone()

if not fila:
    print("No hay colegios en revisar_manualmente.")
    raise SystemExit(0)

colegio = dict(fila)
print(f"=== Inspeccionando colegio id={colegio['id']} ===")
print(f"Nombre:   {colegio['nombre']}")
print(f"Ciudad:   {colegio['ciudad']}")
print(f"Depto:    {colegio['departamento']}")
print(f"Correo:   {colegio['correo_destinatario']}")

# 1) perfil_pedagogico
print("\n--- 1) perfil_pedagogico ---")
pp = colegio.get("perfil_pedagogico")
if not pp:
    print("VACÍO — esto solo bastaría para mandar a revisar_manualmente.")
else:
    try:
        pp_dict = json.loads(pp) if isinstance(pp, str) else pp
        print(f"Tipo: {type(pp_dict).__name__}, keys: {list(pp_dict.keys()) if pp_dict else '[]'}")
        print(json.dumps(pp_dict, ensure_ascii=False, indent=2)[:500])
    except json.JSONDecodeError as e:
        print(f"JSON inválido: {e}")
        print(f"Contenido raw: {pp[:300]}")

# 2) cv_original (PDF pulido completo)
print("\n--- 2) cv_original (de leer_pdf(cv_base_polished.pdf)) ---")
cv_original = _texto_cv_completo(RUTA_POLISHED_PDF)
print(f"Longitud: {len(cv_original)} caracteres")
print(f"Primeros 600 chars:\n{cv_original[:600]}")
print(f"\n...últimos 400 chars:\n{cv_original[-400:]}")

# 3) valores_base (placeholders del polished docx)
print("\n--- 3) valores_base (output de _extraer_cv_base) ---")
try:
    valores_base = _extraer_cv_base(RUTA_PLANTILLA, RUTA_POLISHED_DOCX)
    print(f"Placeholders encontrados: {sorted(valores_base.keys())}")
    print(f"\nPERFIL (primeros 400 chars):\n{valores_base.get('PERFIL', '<<VACIO>>')[:400]}")
    for k in sorted(valores_base.keys()):
        if k.startswith("EXP_") and k.endswith("_TITULO"):
            print(f"\n{k}: {valores_base[k]}")
except Exception as e:
    print(f"ERROR extrayendo: {type(e).__name__}: {e}")

# 4) nombres_permitidos
print("\n--- 4) nombres_permitidos (que el validador ignora) ---")
permitidos = _nombres_permitidos(colegio)
print(f"Set: {sorted(permitidos)}")

# 5) Hechos extraídos del CV original (lo que el validador considera "verdad")
print("\n--- 5) Hechos extraídos del CV original (lo que el validador permite) ---")
hechos_cv = extraer_hechos(cv_original)
print(f"Total: {len(hechos_cv)} hechos verificables")
print(f"Muestra (40 primeros, ordenados):")
for h in sorted(hechos_cv)[:40]:
    print(f"  {h!r}")

# 6) Test sintético: ¿el validador rechazaría una frase obvia del CV?
print("\n--- 6) Test sintético del validador ---")
from modulos.validador import detectar_alucinaciones
# Tomar las primeras 200 chars del propio CV — debería pasar sin alucinaciones
muestra_cv = cv_original[:200]
flagged = detectar_alucinaciones(cv_original, muestra_cv, permitidos)
print(f"Texto = primeros 200 chars del propio CV.")
print(f"Validador encontró alucinaciones? {len(flagged)} hechos flagueados: {sorted(flagged)}")
print(f"(Esperado: 0 — si flaguea su propio CV, el validador tiene un bug)")
