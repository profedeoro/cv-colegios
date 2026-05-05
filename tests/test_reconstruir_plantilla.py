from pathlib import Path
from unittest.mock import patch
from docx import Document

from modulos.pdf_conversor import convertir_docx_a_pdf


def _generar_pdf_de_prueba(tmp_path: Path) -> Path:
    docx = tmp_path / "cv.docx"
    doc = Document()
    doc.add_paragraph("Daniel Villalba")
    doc.add_paragraph("Perfil profesional con experiencia en docencia.")
    doc.save(docx)
    pdf_path = tmp_path / "cv.pdf"
    convertir_docx_a_pdf(docx, pdf_path)
    return pdf_path


def test_reconstruir_plantilla_lee_cv_base(tmp_path):
    cv_pdf = _generar_pdf_de_prueba(tmp_path)
    salida_docx = tmp_path / "plantilla.docx"
    salida_pdf_pulido = tmp_path / "cv_pulido.pdf"

    respuesta_simulada = (
        '{"version_pulida": "Daniel Villalba\\nPerfil profesional con experiencia en docencia.",'
        '"version_con_placeholders": "Daniel Villalba\\n{{PERFIL}}",'
        '"cambios_realizados": [],'
        '"advertencias": []}'
    )

    with patch("reconstruir_plantilla.ClienteClaude") as mock_cliente_cls:
        cliente = mock_cliente_cls.return_value
        cliente.preguntar.return_value = (respuesta_simulada, 0.01)

        from reconstruir_plantilla import ejecutar
        ejecutar(
            cv_pdf=cv_pdf,
            salida_docx=salida_docx,
            salida_pdf=salida_pdf_pulido,
            api_key="sk-test",
            confirmar=lambda _: True,
        )

    assert salida_docx.exists()
    assert salida_pdf_pulido.exists()
    doc = Document(salida_docx)
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "{{PERFIL}}" in texto
