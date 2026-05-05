import os
import pytest
from modulos.config import cargar_config, ConfigError


def test_cargar_config_lee_anthropic_api_key(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-ant-test-123\n")
    config = cargar_config(env_path=env_file)
    assert config["ANTHROPIC_API_KEY"] == "sk-ant-test-123"


def test_cargar_config_falla_si_falta_api_key(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OTRA_VAR=valor\n")
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        cargar_config(env_path=env_file)


def test_cargar_config_falla_si_no_existe_env(tmp_path):
    env_file = tmp_path / "no_existe.env"
    with pytest.raises(ConfigError, match="no encontrado"):
        cargar_config(env_path=env_file)
