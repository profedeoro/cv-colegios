from pathlib import Path
import pytest
from docx import Document
from modulos.plantilla import rellenar_plantilla


def _crear_plantilla(tmp_path) -> Path:
    doc = Document()
    doc.add_heading("{{NOMBRE}}", level=1)
    doc.add_paragraph("{{PERFIL}}")
    doc.add_heading("Experiencia", level=2)
    doc.add_paragraph("{{EXP_1_TITULO}}")
    p = tmp_path / "plantilla.docx"
    doc.save(p)
    return p


def test_rellenar_plantilla_reemplaza_placeholders(tmp_path):
    plantilla = _crear_plantilla(tmp_path)
    salida = tmp_path / "salida.docx"

    rellenar_plantilla(
        plantilla,
        salida,
        valores={
            "NOMBRE": "Daniel Villalba",
            "PERFIL": "Docente con experiencia en TIC.",
            "EXP_1_TITULO": "Colegio Inocencio Chincá",
        },
    )

    doc = Document(salida)
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "Daniel Villalba" in texto
    assert "Docente con experiencia en TIC." in texto
    assert "Colegio Inocencio Chincá" in texto
    assert "{{NOMBRE}}" not in texto


def test_rellenar_falla_si_falta_valor(tmp_path):
    plantilla = _crear_plantilla(tmp_path)
    salida = tmp_path / "salida.docx"
    with pytest.raises(ValueError, match="placeholder"):
        rellenar_plantilla(plantilla, salida, valores={"NOMBRE": "X"})
