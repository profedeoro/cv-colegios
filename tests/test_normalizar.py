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
