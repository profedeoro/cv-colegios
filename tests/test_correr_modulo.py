import sys
from unittest.mock import patch
import pytest
from correr_modulo import main


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
