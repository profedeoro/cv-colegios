from modulos.validador import detectar_alucinaciones


def test_sin_hechos_nuevos_no_aluciona():
    cv = "Daniel trabajó en Universidad de Córdoba en 2024."
    salida = "Daniel trabajó en la Universidad de Córdoba durante 2024."
    assert detectar_alucinaciones(cv_original=cv, texto_generado=salida) == set()


def test_anio_inventado_es_detectado():
    cv = "Daniel se graduó en 2024."
    salida = "Daniel se graduó en 2025."
    nuevos = detectar_alucinaciones(cv_original=cv, texto_generado=salida)
    assert "2025" in nuevos


def test_universidad_inventada_es_detectada():
    cv = "Daniel trabajó en Universidad de Córdoba."
    salida = "Daniel trabajó en Harvard University."
    nuevos = detectar_alucinaciones(cv_original=cv, texto_generado=salida)
    assert any("Harvard" in n for n in nuevos)


def test_nombre_propio_del_destinatario_no_cuenta():
    """Si el colegio se llama 'San Tarsicio', mencionarlo no es alucinación."""
    cv = "Daniel es docente."
    salida = "Estimado rector del Colegio San Tarsicio, Daniel es docente."
    nuevos = detectar_alucinaciones(
        cv_original=cv, texto_generado=salida,
        nombres_permitidos={"Colegio San Tarsicio"},
    )
    assert "Colegio San Tarsicio" not in nuevos
