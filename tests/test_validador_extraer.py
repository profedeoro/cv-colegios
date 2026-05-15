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


def test_palabra_al_inicio_de_oracion_no_extrae():
    """Palabra capitalizada inmediatamente después de '. ' o '! ' o '? ' no debe extraerse."""
    hechos = extraer_hechos("Hola. Bogota es bonita.")
    assert "Bogota" not in hechos


def test_palabra_al_inicio_del_texto_no_extrae():
    """Palabra capitalizada al inicio absoluto del texto no debe extraerse."""
    hechos = extraer_hechos("Bogota es bonita.")
    assert "Bogota" not in hechos


def test_palabra_propia_a_mitad_de_oracion_si_extrae():
    """Pero un nombre propio en medio de la oración SÍ se extrae."""
    hechos = extraer_hechos("Vivo en Bogota desde 2024.")
    assert "Bogota" in hechos


def test_palabra_despues_de_signo_exclamacion():
    """Después de '! ' tampoco se extrae."""
    hechos = extraer_hechos("Increíble! Bogota nos sorprendió.")
    assert "Bogota" not in hechos


def test_extraer_hechos_no_flaguea_pronombre_inicio_parrafo():
    """'Me' al inicio de párrafo tras \\n no debe contar como nombre propio."""
    texto = "Estimado equipo,\n\nMe dirijo a ustedes con respeto."
    assert "Me" not in extraer_hechos(texto)


def test_extraer_hechos_no_flaguea_pronombre_inicio_texto():
    """'Hola' al inicio del texto no debe contar como nombre propio."""
    assert "Hola" not in extraer_hechos("Hola mundo.")


def test_extraer_hechos_si_flaguea_propio_mid_oracion():
    """'Daniel' en medio de oración SÍ debe ser nombre propio."""
    assert "Daniel" in extraer_hechos("El profesor Daniel enseña matemáticas.")


def test_extraer_hechos_no_flaguea_propio_inicio_parrafo_con_indentacion():
    """Espacios/tabs después del \\n no deben rescatar 'Me' como propio."""
    texto = "foo.\n  Mi nombre es..."
    assert "Mi" not in extraer_hechos(texto)
