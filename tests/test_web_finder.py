from unittest.mock import patch
from modulos.web_finder import encontrar_web, _score_match, _tokens_distintivos


def _resultado(url: str, title: str = "", desc: str = "") -> dict:
    return {"url": url, "title": title, "description": desc}


def test_tokens_distintivos_extrae_palabras_clave():
    """Solo deja palabras de >=4 chars que no sean genéricas."""
    tokens = _tokens_distintivos("COL FUND SANTA MARIA")
    # 'col' y 'fund' filtrados; 'santa' y 'maria' filtrados (en lista no-distintivas)
    # → quedan: nada distintivo (todos son palabras-conector o cortas)
    # Test alternativo:
    tokens = _tokens_distintivos("COLEGIO LOS NOGALES")
    assert "nogales" in tokens
    assert "los" not in tokens  # palabra no distintiva
    assert "colegio" not in tokens


def test_score_match_perfecto():
    """Si todos los tokens del nombre aparecen en título/URL → score 1.0."""
    item = _resultado(
        url="https://nogales.edu.co/",
        title="Colegio Los Nogales - Bogotá",
    )
    matches, score = _score_match("Colegio Los Nogales", item)
    assert score == 1.0


def test_score_match_parcial():
    """Si solo algunos tokens coinciden → score parcial."""
    item = _resultado(
        url="https://otrocolegio.edu.co/",
        title="Colegio Anglo Americano",
    )
    # Tokens distintivos de "Colegio Anglo Bilingue Americano": "anglo", "bilingue", "americano"
    matches, score = _score_match("Colegio Anglo Bilingue Americano", item)
    # 2 de 3 tokens matchean → 0.67
    assert 0.5 < score < 1.0


def test_score_match_cero():
    """Si ningún token coincide → score 0."""
    item = _resultado(
        url="https://marymountbq.edu.co/",
        title="Marymount Barranquilla",
    )
    # "Maria Camila" — ninguno aparece en marymount/barranquilla
    matches, score = _score_match("Maria Camila Bilingue", item)
    assert score == 0.0


def test_encontrar_web_acepta_match_alto():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = [
            _resultado(url="https://www.facebook.com/x", title="Facebook"),
            _resultado(url="https://nogales.edu.co/", title="Colegio Los Nogales", desc="..."),
        ]
        web = encontrar_web("Colegio Los Nogales", "Bogotá", api_key="BSA-test")
    assert web == "https://nogales.edu.co/"


def test_encontrar_web_rechaza_match_bajo():
    """Si ningún resultado contiene tokens distintivos del nombre → None.

    Caso real: buscando 'Maria Camila' Brave devuelve Marymount.
    """
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = [
            _resultado(url="https://marymountbq.edu.co/", title="Colegio Marymount Barranquilla"),
            _resultado(url="https://otroquesea.edu.co/", title="Otro Colegio Bilingüe"),
        ]
        web = encontrar_web("ESCUELA MARIA CAMILA", "Barranquilla", api_key="BSA-test")
    assert web is None


def test_encontrar_web_descarta_redes_sociales():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = [
            _resultado(url="https://www.facebook.com/colegio-x", title="Facebook - Colegio Anglo"),
            _resultado(url="https://anglo.edu.co/", title="Colegio Anglo"),
        ]
        web = encontrar_web("Colegio Anglo", "Bogotá", api_key="BSA-test")
    assert "facebook" not in web
    assert ".edu.co" in web


def test_encontrar_web_devuelve_none_sin_resultados():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = []
        web = encontrar_web("Colegio X", "Bogotá", api_key="BSA-test")
    assert web is None


def test_encontrar_web_acepta_otros_tld_si_no_hay_edu_co_pero_match_es_bueno():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = [
            _resultado(url="https://www.bilingueamericano.com/", title="Colegio Bilingüe Americano"),
        ]
        web = encontrar_web("Colegio Bilingue Americano", "Bogotá", api_key="BSA-test")
    assert web == "https://www.bilingueamericano.com/"


def test_encontrar_web_arma_query_correcta():
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = []
        encontrar_web("Colegio San Tarsicio", "Bogotá", api_key="BSA-test")
        args, kwargs = mock.call_args
        query = kwargs.get("query") or (args[0] if args else "")
        assert "Colegio San Tarsicio" in query
        assert "Bogotá" in query


def test_blacklist_atrapa_subdominios_de_directorios():
    """guia-atlantico.educacionencolombia.com.co debe rechazarse igual que el dominio principal."""
    from modulos.web_finder import _es_aceptable
    assert _es_aceptable("https://guia-atlantico.educacionencolombia.com.co/educacion-tradicional/X.htm") is False
    assert _es_aceptable("https://educacionencolombia.com.co/X") is False
    assert _es_aceptable("https://www.buscacolegio.com.co/colegio/X") is False
    # Pero un dominio normal sí pasa
    assert _es_aceptable("https://nogales.edu.co/") is True


def test_encontrar_web_descarta_directorios_de_colegios():
    """Aunque la URL del directorio contenga el nombre del colegio (high score), debe rechazarse."""
    from unittest.mock import patch
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = [
            {"url": "https://guia.educacionencolombia.com.co/maria-camila",
             "title": "Escuela Maria Camila - Educación en Colombia",
             "description": "Maria Camila preescolar barranquilla"},
            # No hay otro resultado válido
        ]
        web = encontrar_web("ESCUELA MARIA CAMILA", "Barranquilla", api_key="BSA-test")
    assert web is None


def test_rechaza_si_solo_matchea_un_token_pero_nombre_tiene_dos():
    """'libertad nino' tokens; URL solo matchea 'libertad' → rechaza (necesita 2 matches)."""
    from unittest.mock import patch
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = [
            {"url": "https://ielalibertad.edu.co/", "title": "IE La Libertad", "description": "colegio publico"},
        ]
        web = encontrar_web("CENTRO EDUCATIVO LIBERTAD DEL NIÑO", "Bogotá", api_key="BSA-test")
    assert web is None


def test_acepta_si_nombre_tiene_un_solo_token_distintivo():
    """'marymount' único token distintivo; basta con 1 match."""
    from unittest.mock import patch
    with patch("modulos.web_finder.buscar_brave") as mock:
        mock.return_value = [
            {"url": "https://marymountbq.edu.co/", "title": "Colegio Marymount Barranquilla"},
        ]
        web = encontrar_web("Colegio Marymount", "Barranquilla", api_key="BSA-test")
    assert web == "https://marymountbq.edu.co/"


def test_blacklist_atrapa_colegioscolombianos():
    from modulos.web_finder import _es_aceptable
    assert _es_aceptable("https://www.colegioscolombianos.com/escuela-x") is False


def test_es_extranjero_detecta_tlds_no_colombianos():
    from modulos.web_finder import _es_aceptable, _es_extranjero
    assert _es_extranjero("https://www.juntadeandalucia.es/educacion") is True
    assert _es_extranjero("https://portaldeeducacion.com.mx/") is True
    assert _es_extranjero("https://colegiox.com.ar/") is True
    assert _es_extranjero("https://escuelaboliviana.com.bo/") is True
    # Colombianos NO son extranjeros
    assert _es_extranjero("https://colegio.edu.co/") is False
    assert _es_extranjero("https://colegio.com.co/") is False
    assert _es_extranjero("https://colegio.org/") is False  # generic OK
    assert _es_extranjero("https://colegio.online/") is False  # generic OK


def test_es_aceptable_rechaza_extranjeros():
    from modulos.web_finder import _es_aceptable
    assert _es_aceptable("https://ceipsanjuanbautista.net/") is True  # .net es generic
    assert _es_aceptable("https://www.juntadeandalucia.es/") is False
    assert _es_aceptable("https://portaldeeducacion.com.mx/") is False
