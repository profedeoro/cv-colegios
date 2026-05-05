from datetime import date
from pathlib import Path
from modulos.logger import obtener_logger


def test_logger_escribe_a_archivo_diario(tmp_path):
    logger = obtener_logger(modulo="prueba", carpeta_logs=tmp_path)
    logger.info("mensaje de prueba")

    archivo_esperado = tmp_path / f"{date.today().isoformat()}.log"
    assert archivo_esperado.exists()
    contenido = archivo_esperado.read_text(encoding="utf-8")
    assert "[prueba]" in contenido
    assert "mensaje de prueba" in contenido


def test_logger_diferentes_modulos_mismo_archivo(tmp_path):
    log1 = obtener_logger(modulo="m1", carpeta_logs=tmp_path)
    log2 = obtener_logger(modulo="m2", carpeta_logs=tmp_path)
    log1.info("desde m1")
    log2.info("desde m2")

    archivo = tmp_path / f"{date.today().isoformat()}.log"
    contenido = archivo.read_text(encoding="utf-8")
    assert "[m1]" in contenido and "desde m1" in contenido
    assert "[m2]" in contenido and "desde m2" in contenido
