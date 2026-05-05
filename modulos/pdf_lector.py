from pathlib import Path
import pdfplumber


def leer_pdf(ruta: Path | str) -> str:
    """Extrae todo el texto de un PDF, página por página."""
    ruta = Path(ruta)
    paginas = []
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                paginas.append(texto)
    return "\n\n".join(paginas)
