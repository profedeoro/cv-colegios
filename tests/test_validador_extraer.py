from modulos.validador import extraer_hechos


def test_extrae_anios():
    assert "2024" in extraer_hechos("Graduado en 2024 de la universidad")


def test_extrae_isbn():
    assert "978-99993-2-001-6" in extraer_hechos("ISBN: 978-99993-2-001-6 publicado")


def test_extrae_doi():
    assert "10.15648/redfids.16.2025.4684" in extraer_hechos(
        "DOI: https://doi.org/10.15648/redfids.16.2025.4684 disponible"
    )


def test_extrae_nombres_propios_multipalabra():
    hechos = extraer_hechos("Trabajé en la Universidad de Córdoba con el profesor Juan Andres Contreras Baltazar.")
    assert "Universidad de Córdoba" in hechos
    assert "Juan Andres Contreras Baltazar" in hechos


def test_no_extrae_palabras_comunes():
    hechos = extraer_hechos("La Educación Física es importante.")
    # 'La' al inicio de oración no debe contar como nombre propio aislado
    assert "La" not in hechos


def test_extrae_porcentajes_y_horas():
    hechos = extraer_hechos("Curso de 60 horas con 95% de asistencia.")
    assert "60" in hechos
    assert "95" in hechos
