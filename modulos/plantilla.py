import re
from pathlib import Path
from docx import Document

RE_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def rellenar_plantilla(
    plantilla_path: Path | str,
    salida_path: Path | str,
    valores: dict[str, str],
) -> None:
    """Carga una plantilla DOCX, reemplaza {{NOMBRE}}-style placeholders, guarda en salida."""
    doc = Document(str(plantilla_path))
    placeholders_encontrados = set()

    def reemplazar_en_runs(parrafo):
        texto_completo = parrafo.text
        for match in RE_PLACEHOLDER.finditer(texto_completo):
            placeholders_encontrados.add(match.group(1))
        nuevo_texto = RE_PLACEHOLDER.sub(
            lambda m: valores.get(m.group(1), m.group(0)),
            texto_completo,
        )
        if nuevo_texto != texto_completo:
            for run in parrafo.runs:
                run.text = ""
            if parrafo.runs:
                parrafo.runs[0].text = nuevo_texto
            else:
                parrafo.add_run(nuevo_texto)

    for parrafo in doc.paragraphs:
        reemplazar_en_runs(parrafo)
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                for parrafo in celda.paragraphs:
                    reemplazar_en_runs(parrafo)

    faltantes = placeholders_encontrados - set(valores.keys())
    if faltantes:
        raise ValueError(f"placeholder(s) sin valor: {sorted(faltantes)}")

    Path(salida_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(salida_path))
