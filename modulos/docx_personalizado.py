from pathlib import Path

from modulos.plantilla import rellenar_plantilla
from modulos.pdf_conversor import convertir_docx_a_pdf


def generar_pdf_personalizado(
    plantilla_path: Path | str,
    valores: dict[str, str],
    salida_pdf: Path | str,
) -> None:
    """Rellena una plantilla DOCX con valores y la convierte a PDF.

    1. Crea un DOCX temporal con los placeholders reemplazados.
    2. Convierte ese DOCX temporal a PDF en salida_pdf.
    3. Elimina el DOCX temporal.

    Levanta:
      - ValueError si la plantilla tiene placeholders sin valor (propagado de rellenar_plantilla).
      - ConversionError si LibreOffice falla (propagado de convertir_docx_a_pdf).
    """
    salida_pdf = Path(salida_pdf)
    salida_pdf.parent.mkdir(parents=True, exist_ok=True)

    tmp_docx = salida_pdf.with_suffix(".__tmp__.docx")
    try:
        rellenar_plantilla(plantilla_path, tmp_docx, valores)
        convertir_docx_a_pdf(tmp_docx, salida_pdf)
    finally:
        if tmp_docx.exists():
            tmp_docx.unlink()
