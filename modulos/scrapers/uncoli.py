"""Scraper de la lista de miembros de UNCOLI (Unión de Colegios Internacionales)."""
from selectolax.parser import HTMLParser
from modulos.http_cliente import fetch_html
from modulos.scrapers.tipos import ColegioInfo

URL_UNCOLI = "https://www.uncoli.org/colegios-asociados/"

# Selector CSS — ajustar si UNCOLI cambia su HTML.
SELECTOR_MIEMBRO = "article.member"
SELECTOR_NOMBRE = "h3.member-name, .member-name"
SELECTOR_LINK = "a.member-link, .member-link"


def parsear_html_uncoli(html: str) -> list[ColegioInfo]:
    """Extrae colegios de un HTML de la página de miembros UNCOLI."""
    tree = HTMLParser(html)
    colegios = []
    for nodo_miembro in tree.css(SELECTOR_MIEMBRO):
        nombre_node = nodo_miembro.css_first(SELECTOR_NOMBRE)
        if not nombre_node:
            continue
        nombre = nombre_node.text(strip=True)
        link_node = nodo_miembro.css_first(SELECTOR_LINK)
        web = link_node.attributes.get("href") if link_node else None
        colegios.append(ColegioInfo(
            nombre=nombre,
            ciudad="Bogotá",
            departamento="Bogotá D.C.",
            fuente="UNCOLI",
            web=web,
        ))
    return colegios


def scrape_uncoli() -> list[ColegioInfo]:
    """Descarga la página de UNCOLI y extrae los colegios."""
    html = fetch_html(URL_UNCOLI)
    return parsear_html_uncoli(html)
