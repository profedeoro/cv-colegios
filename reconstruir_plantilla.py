"""Pule el CV base con Claude y produce plantilla.docx + cv_pulido.pdf.

Uso:
    python reconstruir_plantilla.py
"""
import json
from pathlib import Path
from typing import Callable

from docx import Document

from modulos.cliente_claude import ClienteClaude
from modulos.config import cargar_config
from modulos.pdf_conversor import convertir_docx_a_pdf
from modulos.pdf_lector import leer_pdf

RUTA_CV_BASE = Path(__file__).parent / "data" / "cv_base.pdf"
RUTA_SALIDA_DOCX = Path(__file__).parent / "data" / "plantilla_base.docx"
RUTA_SALIDA_PDF = Path(__file__).parent / "data" / "cv_base_polished.pdf"
RUTA_PROMPT = Path(__file__).parent / "prompts" / "pulir_cv.txt"


def _texto_a_docx(texto: str, salida: Path) -> None:
    """Convierte texto plano (con \\n como saltos) a un DOCX simple."""
    doc = Document()
    for parrafo in texto.split("\n"):
        doc.add_paragraph(parrafo)
    salida.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(salida))


def ejecutar(
    cv_pdf: Path = RUTA_CV_BASE,
    salida_docx: Path = RUTA_SALIDA_DOCX,
    salida_pdf: Path = RUTA_SALIDA_PDF,
    api_key: str | None = None,
    confirmar: Callable[[dict], bool] | None = None,
) -> None:
    """Pule el CV. `confirmar` recibe el dict de respuesta de Claude y devuelve True para guardar."""
    if api_key is None:
        config = cargar_config()
        api_key = config["ANTHROPIC_API_KEY"]

    if not cv_pdf.exists():
        raise FileNotFoundError(
            f"No se encontró {cv_pdf}. Coloca tu HV en esa ruta antes de correr."
        )

    texto_cv = leer_pdf(cv_pdf)
    sistema = RUTA_PROMPT.read_text(encoding="utf-8")
    cliente = ClienteClaude(api_key=api_key)
    respuesta, costo = cliente.preguntar(sistema=sistema, usuario=texto_cv, max_tokens=8000)

    # Limpiar code fence si Claude lo envolvió
    raw = respuesta.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    datos = json.loads(raw.strip())

    if confirmar is not None and not confirmar(datos):
        print("Cancelado por el usuario. No se guardó nada.")
        return

    # Guardar plantilla con placeholders
    _texto_a_docx(datos["version_con_placeholders"], salida_docx)

    # Guardar versión pulida (DOCX → PDF)
    docx_pulido = salida_pdf.with_suffix(".docx")
    _texto_a_docx(datos["version_pulida"], docx_pulido)
    convertir_docx_a_pdf(docx_pulido, salida_pdf)
    docx_pulido.unlink(missing_ok=True)

    print(f"Plantilla guardada en {salida_docx}")
    print(f"Version pulida guardada en {salida_pdf}")
    print(f"Costo de la operación: ${costo:.4f} USD")


def _confirmar_interactivo(datos: dict) -> bool:
    print("\n=== Cambios propuestos por Claude ===")
    for cambio in datos.get("cambios_realizados", []):
        print(f"  - {cambio}")
    if datos.get("advertencias"):
        print("\n=== Advertencias ===")
        for adv in datos["advertencias"]:
            print(f"  ⚠ {adv}")
    respuesta = input("\n¿Aceptas estos cambios y guardas la plantilla? [s/N]: ").strip().lower()
    return respuesta == "s"


if __name__ == "__main__":
    ejecutar(confirmar=_confirmar_interactivo)
