import pytest
from unittest.mock import MagicMock, patch
from modulos.cliente_claude import ClienteClaude


def test_cliente_envia_prompt_y_devuelve_texto():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="respuesta de prueba")]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50

    with patch("modulos.cliente_claude.Anthropic") as mock_anthropic:
        instancia = mock_anthropic.return_value
        instancia.messages.create.return_value = mock_response

        cliente = ClienteClaude(api_key="sk-ant-test")
        texto, costo = cliente.preguntar(
            sistema="Eres un asistente.",
            usuario="Hola",
        )

        assert texto == "respuesta de prueba"
        assert costo > 0


def test_cliente_falla_sin_api_key():
    with pytest.raises(ValueError, match="api_key"):
        ClienteClaude(api_key="")
