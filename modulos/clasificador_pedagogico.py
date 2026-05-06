"""Clasificador de perfil pedagógico usando Claude."""
import json
from pathlib import Path

RUTA_PROMPT = Path(__file__).parent.parent / "prompts" / "clasificar_colegio.txt"
MAX_TOKENS = 1500
MAX_CHARS_INPUT = 10000  # límite para no inflar tokens


def _parsear_json(respuesta: str) -> dict:
    """Parsea JSON tolerante a code fences."""
    raw = respuesta.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.lower().lstrip().startswith("json"):
            if "\n" in raw:
                raw = raw[raw.index("\n") + 1:]
        raw = raw.rsplit("```", 1)[0]
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Respuesta de Claude no es JSON válido: {e}") from e


def clasificar(texto_sitio: str, cliente_claude) -> tuple[dict, float]:
    """Pide a Claude clasificar el perfil pedagógico. Devuelve (perfil, costo_usd)."""
    sistema = RUTA_PROMPT.read_text(encoding="utf-8")
    usuario = texto_sitio[:MAX_CHARS_INPUT]
    respuesta, costo = cliente_claude.preguntar(
        sistema=sistema,
        usuario=usuario,
        max_tokens=MAX_TOKENS,
        cachear_sistema=True,
    )
    perfil = _parsear_json(respuesta)
    return perfil, costo
