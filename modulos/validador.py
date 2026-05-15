import re
import unicodedata

RE_ANIO = re.compile(r"\b(?:19|20)\d{2}\b")
RE_NUMERO = re.compile(r"\b\d{1,4}\b")
RE_ISBN = re.compile(r"\b(?:97[89][- ]?)?\d{1,5}[- ]?\d{1,7}[- ]?\d{1,7}[- ]?[\dX]\b")
RE_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
RE_PROPIO = re.compile(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:[ \t]+(?:de[ \t]+|del[ \t]+|la[ \t]+|las[ \t]+|los[ \t]+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*\b")


def _quitar_acentos(s: str) -> str:
    """Devuelve `s` sin marcas de acento (NFD + filter Mn)."""
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _es_inicio_oracion(texto: str, pos: int) -> bool:
    """True si `pos` es inicio: del texto, de un párrafo (\\n), o tras .!?.

    A diferencia de `.rstrip()`, solo come espacios/tabs — preserva `\\n` como
    señal de "salto de párrafo".
    """
    if pos == 0:
        return True
    i = pos - 1
    while i >= 0 and texto[i] in " \t":
        i -= 1
    if i < 0:
        return True
    return texto[i] in ".!?\n"


def extraer_hechos(texto: str) -> set[str]:
    """Devuelve el conjunto de tokens 'verificables' (años, números, nombres propios, ISBNs, DOIs)."""
    hechos = set()
    hechos.update(RE_ANIO.findall(texto))
    hechos.update(RE_ISBN.findall(texto))
    hechos.update(RE_DOI.findall(texto))
    hechos.update(RE_NUMERO.findall(texto))
    for match in RE_PROPIO.finditer(texto):
        candidato = match.group(0)
        if " " in candidato:
            hechos.add(candidato)
        elif not _es_inicio_oracion(texto, match.start()):
            hechos.add(candidato)
    return hechos


def _es_subfrase(corta: str, larga: str) -> bool:
    """True si las palabras de `corta` aparecen contiguamente en `larga`.

    Comparación a nivel de palabras (split por whitespace). Insensible al
    case/acentos — el caller debe normalizar antes si quiere ese comportamiento.
    """
    palabras_c = corta.split()
    palabras_l = larga.split()
    if not palabras_c or len(palabras_c) > len(palabras_l):
        return False
    for i in range(len(palabras_l) - len(palabras_c) + 1):
        if palabras_l[i:i+len(palabras_c)] == palabras_c:
            return True
    return False


def detectar_alucinaciones(
    cv_original: str,
    texto_generado: str,
    nombres_permitidos: set[str] | None = None,
) -> set[str]:
    """Devuelve los hechos del texto_generado que NO están en cv_original ni en nombres_permitidos.

    Comparación insensible a acentos. Acepta subfrases contiguas: si un hecho
    generado (p. ej. 'Daniel') aparece como subsecuencia de palabras de un
    hecho del CV o de permitidos (p. ej. 'Daniel Eduardo Villalba de Oro'), se
    considera consistente con la fuente.
    """
    hechos_cv = {_quitar_acentos(h) for h in extraer_hechos(cv_original)}
    permitidos = {_quitar_acentos(p) for p in (nombres_permitidos or set())}
    flagged = set()
    for hecho in extraer_hechos(texto_generado):
        h_norm = _quitar_acentos(hecho)
        if any(_es_subfrase(h_norm, c) for c in hechos_cv):
            continue
        if any(_es_subfrase(h_norm, p) for p in permitidos):
            continue
        flagged.add(hecho)
    return flagged
