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
