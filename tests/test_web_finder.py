from unittest.mock import patch
from modulos.web_finder import encontrar_web


def _resultados_mock(urls: list[str]) -> list[dict]:
    return [{"title": f"Colegio {i}", "url": u, "description": ""} for i, u in enumerate(urls)]


def test_encontrar_web_devuelve_primer_edu_co():
    """Prefiere dominios .edu.co sobre otros."""
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = _resultados_mock([
            "https://www.facebook.com/colegio-x",
            "https://colegiox.edu.co/",
            "https://otro.edu.co/",
        ])
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert web == "https://colegiox.edu.co/"


def test_encontrar_web_descarta_redes_sociales():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = _resultados_mock([
            "https://www.facebook.com/colegio-x",
            "https://twitter.com/colegio",
            "https://www.linkedin.com/in/colegio",
            "https://www.instagram.com/colegio",
            "https://colegio-x.edu.co/",
        ])
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert "facebook" not in web
    assert "twitter" not in web
    assert ".edu.co" in web


def test_encontrar_web_acepta_otros_tld_si_no_hay_edu_co():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = _resultados_mock([
            "https://www.colegio-x.com/",
            "https://www.colegio-x.org/",
        ])
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert web == "https://www.colegio-x.com/"


def test_encontrar_web_devuelve_none_sin_resultados():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = []
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert web is None


def test_encontrar_web_devuelve_none_si_solo_redes_sociales():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = _resultados_mock([
            "https://www.facebook.com/x",
            "https://twitter.com/x",
        ])
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert web is None


def test_encontrar_web_arma_query_correcta():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = []
        encontrar_web("Colegio San Tarsicio", "Bogotá", api_key="BSA-test")
        args, kwargs = mock.call_args
        query = kwargs.get("query") or args[0]
        assert "Colegio San Tarsicio" in query
        assert "Bogotá" in query
