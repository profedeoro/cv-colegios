from anthropic import Anthropic


MODELO = "claude-sonnet-4-6"

# Tarifas USD por millón de tokens (Sonnet 4.6 al 2026-05; ajustar si cambia)
PRECIO_INPUT = 3.0
PRECIO_OUTPUT = 15.0


class ClienteClaude:
    """Wrapper sobre el SDK de Anthropic con cálculo de costo y prompt caching."""

    def __init__(self, api_key: str, modelo: str = MODELO):
        if not api_key:
            raise ValueError("api_key es requerida")
        self.cliente = Anthropic(api_key=api_key)
        self.modelo = modelo

    def preguntar(
        self,
        sistema: str,
        usuario: str,
        max_tokens: int = 4096,
        cachear_sistema: bool = False,
    ) -> tuple[str, float]:
        """Envía un prompt y devuelve (texto_respuesta, costo_estimado_usd)."""
        sistema_param = sistema
        if cachear_sistema:
            sistema_param = [{
                "type": "text",
                "text": sistema,
                "cache_control": {"type": "ephemeral"},
            }]

        respuesta = self.cliente.messages.create(
            model=self.modelo,
            max_tokens=max_tokens,
            system=sistema_param,
            messages=[{"role": "user", "content": usuario}],
        )

        texto = "".join(b.text for b in respuesta.content if hasattr(b, "text"))
        costo = (
            respuesta.usage.input_tokens * PRECIO_INPUT
            + respuesta.usage.output_tokens * PRECIO_OUTPUT
        ) / 1_000_000
        return texto, costo
