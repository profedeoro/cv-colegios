"""Scraper de la lista de miembros de CONACED."""
from selectolax.parser import HTMLParser
from modulos.http_cliente import fetch_html
from modulos.scrapers.tipos import ColegioInfo

URL_CONACED = "https://www.conaced.edu.co/colegios"
SELECTOR_ITEM = "li.colegio-item"
SELECTOR_NOMBRE = ".nombre, .colegio-nombre"

DEPARTAMENTOS_OBJETIVO = {"Bogotá D.C.", "Antioquia", "Atlántico"}
CIUDADES_ATLANTICO = {"Barranquilla"}


def _es_region_objetivo(departamento: str, ciudad: str) -> bool:
    if departamento not in DEPARTAMENTOS_OBJETIVO:
        return False
    if departamento == "Atlántico" and ciudad not in CIUDADES_ATLANTICO:
        return False
    return True


def parsear_html_conaced(html: str) -> list[ColegioInfo]:
    tree = HTMLParser(html)
    colegios = []
    for item in tree.css(SELECTOR_ITEM):
        nombre_node = item.css_first(SELECTOR_NOMBRE)
        if not nombre_node:
            continue
        nombre = nombre_node.text(strip=True)
        ciudad = item.attributes.get("data-ciudad", "")
        depto = item.attributes.get("data-depto", "")
        if not _es_region_objetivo(depto, ciudad):
            continue
        colegios.append(ColegioInfo(
            nombre=nombre,
            ciudad=ciudad,
            departamento=depto,
            fuente="CONACED",
        ))
    return colegios


def scrape_conaced() -> list[ColegioInfo]:
    html = fetch_html(URL_CONACED)
    return parsear_html_conaced(html)
