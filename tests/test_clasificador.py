import json
from unittest.mock import MagicMock
import pytest
from modulos.clasificador_pedagogico import clasificar


def _mock_claude(respuesta: str):
    cliente = MagicMock()
    cliente.preguntar.return_value = (respuesta, 0.001)
    return cliente


def test_clasificar_devuelve_dict_con_campos_esperados():
    respuesta = json.dumps({
        "bilingue": True,
        "idioma_segundo": "inglés",
        "religioso": False,
        "denominacion": None,
        "ib": True,
        "montessori": False,
        "enfoque_deportivo": False,
        "enfoque_tecnico": False,
        "enfasis_tic": True,
        "tamano_estimado": "grande",
        "palabras_clave": ["bilingüe", "IB", "innovación"],
    })
    cliente = _mock_claude(respuesta)
    perfil, costo = clasificar("texto del sitio web", cliente)
    assert perfil["bilingue"] is True
    assert perfil["idioma_segundo"] == "inglés"
    assert perfil["ib"] is True
    assert costo == 0.001


def test_clasificar_acepta_respuesta_con_code_fence():
    respuesta = "```json\n" + json.dumps({"bilingue": False, "religioso": False, "denominacion": None,
                                           "idioma_segundo": None, "ib": False, "montessori": False,
                                           "enfoque_deportivo": False, "enfoque_tecnico": False,
                                           "enfasis_tic": False, "tamano_estimado": "desconocido",
                                           "palabras_clave": []}) + "\n```"
    cliente = _mock_claude(respuesta)
    perfil, _ = clasificar("texto", cliente)
    assert perfil["bilingue"] is False


def test_clasificar_lanza_si_json_malformado():
    cliente = _mock_claude("esto no es json")
    with pytest.raises(ValueError):
        clasificar("texto", cliente)
