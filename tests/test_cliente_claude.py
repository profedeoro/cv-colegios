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
        assert costo == pytest.approx(0.00105)


def test_cliente_falla_sin_api_key():
    with pytest.raises(ValueError, match="api_key"):
        ClienteClaude(api_key="")


def test_cachear_sistema_envuelve_en_lista_con_cache_control():
    """Cuando cachear_sistema=True, el system param debe ser lista con cache_control ephemeral."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="ok")]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    with patch("modulos.cliente_claude.Anthropic") as mock_anthropic:
        instancia = mock_anthropic.return_value
        instancia.messages.create.return_value = mock_response

        cliente = ClienteClaude(api_key="sk-ant-test")
        cliente.preguntar(sistema="Soy un sistema.", usuario="U", cachear_sistema=True)

        _, kwargs = instancia.messages.create.call_args
        assert isinstance(kwargs["system"], list)
        assert kwargs["system"][0]["type"] == "text"
        assert kwargs["system"][0]["text"] == "Soy un sistema."
        assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
