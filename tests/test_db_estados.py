import pytest
from modulos.db import (
    inicializar_db, insertar_colegio, cambiar_estado,
    obtener_estado, EstadoInvalidoError,
)


def _crear(tmp_path):
    ruta = tmp_path / "t.db"
    inicializar_db(ruta)
    cid = insertar_colegio(ruta, nombre="X Distintivo", ciudad="Bogotá",
                            departamento="Bogotá D.C.", fuente="MEN")
    return ruta, cid


def test_transicion_valida(tmp_path):
    ruta, cid = _crear(tmp_path)
    cambiar_estado(ruta, cid, "enriquecido")
    assert obtener_estado(ruta, cid) == "enriquecido"


def test_transicion_invalida_falla(tmp_path):
    ruta, cid = _crear(tmp_path)
    cambiar_estado(ruta, cid, "enriquecido")
    with pytest.raises(EstadoInvalidoError, match="no se puede pasar"):
        cambiar_estado(ruta, cid, "descubierto")


def test_descartado_desde_cualquier_estado(tmp_path):
    ruta, cid = _crear(tmp_path)
    cambiar_estado(ruta, cid, "enriquecido")
    cambiar_estado(ruta, cid, "borrador_creado")
    cambiar_estado(ruta, cid, "descartado")
    assert obtener_estado(ruta, cid) == "descartado"


def test_estado_inexistente_falla(tmp_path):
    ruta, cid = _crear(tmp_path)
    with pytest.raises(EstadoInvalidoError, match="estado desconocido"):
        cambiar_estado(ruta, cid, "estado_que_no_existe")
