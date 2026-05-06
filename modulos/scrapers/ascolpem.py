"""Scraper de ASCOLPEM. Tolerante a fallos: devuelve [] si la URL no existe."""
from selectolax.parser import HTMLParser
from modulos.http_cliente import fetch_html, HttpError
from modulos.scrapers.tipos import ColegioInfo

URL_ASCOLPEM = "https://www.ascolpem.com/afiliados"

DEPARTAMENTOS_OBJETIVO = {"Bogotá D.C.", "Antioquia", "Atlántico"}
CIUDADES_ATLANTICO = {"Barranquilla"}


def _es_region_objetivo(departamento: str, ciudad: str) -> bool:
    if departamento not in DEPARTAMENTOS_OBJETIVO:
        return False
    if departamento == "Atlántico" and ciudad not in CIUDADES_ATLANTICO:
        return False
    return True


def parsear_html_ascolpem(html: str) -> list[ColegioInfo]:
    tree = HTMLParser(html)
    colegios = []
    for fila in tree.css("table#afiliados tr"):
        celdas = fila.css("td")
        if len(celdas) < 3:
            continue  # encabezado o fila vacía
        nombre = celdas[0].text(strip=True)
        ciudad = celdas[1].text(strip=True)
        departamento = celdas[2].text(strip=True)
        if not _es_region_objetivo(departamento, ciudad):
            continue
        colegios.append(ColegioInfo(
            nombre=nombre,
            ciudad=ciudad,
            departamento=departamento,
            fuente="ASCOLPEM",
        ))
    return colegios


def scrape_ascolpem() -> list[ColegioInfo]:
    """Tolerante: devuelve [] si la URL falla."""
    try:
        html = fetch_html(URL_ASCOLPEM)
    except HttpError:
        return []
    return parsear_html_ascolpem(html)
