import shutil
import subprocess
from pathlib import Path


class ConversionError(Exception):
    pass


def _ruta_libreoffice() -> str:
    """Encuentra el ejecutable de LibreOffice. Prefiere 'soffice' en PATH; cae a Windows estándar."""
    if shutil.which("soffice"):
        return "soffice"
    candidatos = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for c in candidatos:
        if Path(c).exists():
            return c
    raise ConversionError("LibreOffice no encontrado. Instálalo desde libreoffice.org")


def convertir_docx_a_pdf(docx_path: Path | str, pdf_path: Path | str) -> None:
    """Convierte un DOCX a PDF usando LibreOffice headless."""
    docx_path = Path(docx_path)
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    soffice = _ruta_libreoffice()
    resultado = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", str(docx_path),
         "--outdir", str(pdf_path.parent)],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        raise ConversionError(f"LibreOffice falló: {resultado.stderr}")

    # LibreOffice nombra el output con el mismo nombre del docx, extensión pdf
    salida_lo = pdf_path.parent / (docx_path.stem + ".pdf")
    if salida_lo != pdf_path:
        salida_lo.rename(pdf_path)
