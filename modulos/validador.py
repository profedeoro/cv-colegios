import re

RE_ANIO = re.compile(r"\b(?:19|20)\d{2}\b")
RE_NUMERO = re.compile(r"\b\d{1,4}\b")
RE_ISBN = re.compile(r"\b(?:97[89][- ]?)?\d{1,5}[- ]?\d{1,7}[- ]?\d{1,7}[- ]?[\dX]\b")
RE_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
RE_PROPIO = re.compile(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de\s+|del\s+|la\s+|las\s+|los\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*\b")


def extraer_hechos(texto: str) -> set[str]:
    """Devuelve el conjunto de tokens 'verificables' (años, números, nombres propios, ISBNs, DOIs)."""
    hechos = set()
    hechos.update(RE_ANIO.findall(texto))
    hechos.update(RE_ISBN.findall(texto))
    hechos.update(RE_DOI.findall(texto))
    hechos.update(RE_NUMERO.findall(texto))
    # Nombres propios de 2+ palabras, descartando palabras al inicio de oración
    for match in RE_PROPIO.finditer(texto):
        candidato = match.group(0)
        if " " in candidato:
            hechos.add(candidato)
        else:
            inicio = match.start()
            # Strip trailing whitespace from everything before the match, then check
            # if the last non-whitespace character is sentence-ending punctuation.
            antes = texto[:inicio].rstrip()
            if antes and antes[-1] not in ".!?":
                hechos.add(candidato)
    return hechos


def detectar_alucinaciones(
    cv_original: str,
    texto_generado: str,
    nombres_permitidos: set[str] | None = None,
) -> set[str]:
    """Devuelve los hechos del texto_generado que NO están en cv_original ni en nombres_permitidos."""
    hechos_cv = extraer_hechos(cv_original)
    hechos_generado = extraer_hechos(texto_generado)
    permitidos = nombres_permitidos or set()
    return hechos_generado - hechos_cv - permitidos
