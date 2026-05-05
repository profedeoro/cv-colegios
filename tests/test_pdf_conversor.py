from pathlib import Path
from docx import Document
from modulos.pdf_conversor import convertir_docx_a_pdf


def test_convierte_docx_a_pdf(tmp_path):
    docx_path = tmp_path / "entrada.docx"
    pdf_path = tmp_path / "entrada.pdf"
    doc = Document()
    doc.add_paragraph("Texto de prueba para conversion.")
    doc.save(docx_path)

    convertir_docx_a_pdf(docx_path, pdf_path)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 100  # PDF no vacío
