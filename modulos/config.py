from pathlib import Path
from dotenv import dotenv_values


class ConfigError(Exception):
    """Error en la configuración del proyecto."""


REQUERIDAS = ["ANTHROPIC_API_KEY"]


def cargar_config(env_path: Path | str = "config/.env") -> dict[str, str]:
    """Carga la configuración desde un archivo .env y valida que las claves requeridas estén presentes."""
    env_path = Path(env_path)
    if not env_path.exists():
        raise ConfigError(f"Archivo de configuración no encontrado: {env_path}")

    valores = dotenv_values(env_path)
    faltantes = [k for k in REQUERIDAS if not valores.get(k)]
    if faltantes:
        raise ConfigError(f"Variables faltantes en {env_path}: {', '.join(faltantes)}")

    return {k: v for k, v in valores.items() if v is not None}
