import sys
from unittest.mock import patch
import pytest
from correr_modulo import main


def _crear_bd(tmp_path):
    bd = tmp_path / "t.db"
    from modulos.db import inicializar_db
    inicializar_db(bd)
    return bd


def _crear_env(tmp_path, contenido: str = "ANTHROPIC_API_KEY=sk-test\n"):
    env = tmp_path / ".env"
    env.write_text(contenido)
    return env


def test_main_descubrir_invoca_ejecutar(tmp_path, monkeypatch):
    bd = tmp_path / "t.db"
    from modulos.db import inicializar_db
    inicializar_db(bd)

    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=sk-test\nGOOGLE_CSE_API_KEY=k\nGOOGLE_CSE_ENGINE_ID=e\n")

    with patch("correr_modulo.descubrir_ejecutar") as mock_eje:
        mock_eje.return_value = {"MEN": 0, "UNCOLI": 0, "CONACED": 0, "ASCOLPEM": 0, "Google": 0}
        monkeypatch.setattr(sys, "argv", ["correr_modulo.py", "descubrir",
                                          "--bd", str(bd), "--env", str(env)])
        main()
    assert mock_eje.called


def test_main_modulo_desconocido_falla(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["correr_modulo.py", "inexistente"])
    with pytest.raises(SystemExit):
        main()


def test_main_enriquecer_invoca_ejecutar(tmp_path, monkeypatch):
    bd = tmp_path / "t.db"
    from modulos.db import inicializar_db
    inicializar_db(bd)
    env = tmp_path / ".env"
    env.write_text(
        "ANTHROPIC_API_KEY=sk-test\n"
        "BRAVE_SEARCH_API_KEY=BSA-test\n"
    )
    with patch("correr_modulo.enriquecer_ejecutar") as mock_eje:
        mock_eje.return_value = {"resumen": {"enriquecido": 5, "sin_correo": 2, "error": 0},
                                 "costo_usd": 0.5, "duracion_seg": 30}
        monkeypatch.setattr(sys, "argv", ["correr_modulo.py", "enriquecer",
                                          "--bd", str(bd), "--env", str(env), "--max", "10"])
        main()
    assert mock_eje.called


def test_main_generar_invoca_ejecutar_con_max(tmp_path, monkeypatch, capsys):
    bd = _crear_bd(tmp_path)
    env = _crear_env(tmp_path)
    with patch("correr_modulo.generar_ejecutar") as mock_eje:
        mock_eje.return_value = {
            "resumen": {"borrador_insertado": 4, "revisar_manualmente": 1},
            "costo_usd": 0.1234,
            "duracion_seg": 12.5,
        }
        monkeypatch.setattr(sys, "argv", ["correr_modulo.py", "generar",
                                          "--bd", str(bd), "--env", str(env), "--max", "5"])
        main()
    assert mock_eje.called
    _, kwargs = mock_eje.call_args
    assert kwargs["max_colegios"] == 5
    assert kwargs["cliente_claude"] is not None
    salida = capsys.readouterr().out
    assert "borrador_insertado" in salida
    assert "0.1234" in salida


def test_main_generar_usa_default_max_15(tmp_path, monkeypatch):
    bd = _crear_bd(tmp_path)
    env = _crear_env(tmp_path)
    with patch("correr_modulo.generar_ejecutar") as mock_eje:
        mock_eje.return_value = {
            "resumen": {"borrador_insertado": 0},
            "costo_usd": 0.0,
            "duracion_seg": 0.1,
        }
        monkeypatch.setattr(sys, "argv", ["correr_modulo.py", "generar",
                                          "--bd", str(bd), "--env", str(env)])
        main()
    assert mock_eje.called
    _, kwargs = mock_eje.call_args
    assert kwargs["max_colegios"] == 15


def test_main_enviar_borradores_invoca_ejecutar(tmp_path, monkeypatch, capsys):
    bd = _crear_bd(tmp_path)
    env = _crear_env(tmp_path)
    token = tmp_path / "gmail_token.json"
    token.write_text("{}")
    with patch("correr_modulo.enviar_borradores_ejecutar") as mock_eje:
        mock_eje.return_value = {
            "total": 3, "subidos": 2, "fallos": 0, "correo_invalido": 1,
        }
        monkeypatch.setattr(sys, "argv", ["correr_modulo.py", "enviar_borradores",
                                          "--bd", str(bd), "--env", str(env),
                                          "--token", str(token)])
        main()
    assert mock_eje.called
    args, kwargs = mock_eje.call_args
    # ruta_token debe ser el path provisto
    assert str(token) in [str(a) for a in args] or str(token) == str(kwargs.get("ruta_token"))
    salida = capsys.readouterr().out
    assert "subidos" in salida.lower() or "Subidos" in salida
