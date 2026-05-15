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


def test_detectar_alucinaciones_es_insensible_a_acentos():
    """'María' generado debe matchear con 'Maria' en permitidos."""
    cv = "Daniel trabajó en docencia."
    gen = "Trabajó en el Colegio Santa María."
    permitidos = {"Colegio Santa Maria"}
    assert detectar_alucinaciones(cv, gen, permitidos) == set()


def test_detectar_alucinaciones_cv_sin_acentos_matchea_generado_con_acentos():
    """Si CV original viene sin acentos (escaneado/OCR), generado con acentos no se flaguea."""
    cv = "Daniel vivio en Bogota durante 2020."
    gen = "Daniel vivió en Bogotá durante 2020."
    assert detectar_alucinaciones(cv, gen) == set()


def test_detectar_alucinaciones_si_flaguea_hechos_genuinamente_inventados():
    """Comparación accent-insensitive NO debe encubrir alucinaciones reales."""
    cv = "Daniel trabajó en Bogotá."
    gen = "Daniel publicó en la Universidad Nacional con el profesor Pedro Castaño."
    flagged = detectar_alucinaciones(cv, gen)
    # "Universidad Nacional" y "Pedro Castaño" NO están en cv → flagueados
    assert any("Universidad" in f or "Pedro" in f for f in flagged)


def test_detectar_alucinaciones_devuelve_forma_original_acentuada():
    """Cuando algo SÍ es alucinación, devolver la forma original (con acentos)."""
    cv = "Daniel es profesor."
    gen = "Daniel trabajó en la Universidad de Antioquía."  # 'Antioquía' inventado
    flagged = detectar_alucinaciones(cv, gen)
    # Debe contener la forma original con acento, no la normalizada
    assert any("Antioquía" in f for f in flagged)
