from modulos.normalizar import normalizar_nombre


def test_normaliza_minusculas_y_acentos():
    assert normalizar_nombre("Colegio San José") == "san jose"


def test_remueve_sufijos_legales():
    assert normalizar_nombre("Colegio San Carlos S.A.S.") == "san carlos"
    assert normalizar_nombre("Institución Educativa Santa María Ltda.") == "santa maria"


def test_colapsa_espacios():
    assert normalizar_nombre("  Colegio   Bilingüe   ABC  ") == "bilingue abc"


def test_remueve_palabras_genericas():
    assert normalizar_nombre("Corporación Colegio Gimnasio Moderno") == "moderno"


from modulos.normalizar import normalizar_ciudad


def test_normaliza_bogota_dc():
    assert normalizar_ciudad("BOGOTÁ D.C.") == "Bogotá"
    assert normalizar_ciudad("Bogotá D.C") == "Bogotá"
    assert normalizar_ciudad("bogotá d c") == "Bogotá"


def test_normaliza_ciudad_simple():
    assert normalizar_ciudad("MEDELLÍN") == "Medellín"
    assert normalizar_ciudad("BARRANQUILLA") == "Barranquilla"
    assert normalizar_ciudad("Bogotá") == "Bogotá"


def test_normaliza_ciudad_multipalabra_se_preserva():
    """Crítico: ciudades reales multi-palabra de Colombia NO deben truncarse."""
    assert "Carmen" in normalizar_ciudad("El Carmen de Viboral")
    assert "Viboral" in normalizar_ciudad("El Carmen de Viboral")
    assert "Vicente" in normalizar_ciudad("San Vicente del Caguán")
    assert "Estrella" in normalizar_ciudad("La Estrella")


def test_ciudad_vacia_devuelve_vacia():
    assert normalizar_ciudad("") == ""
    assert normalizar_ciudad("   ") == "   "
