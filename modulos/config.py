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


GOOGLE_CSE_REQUERIDAS = ["GOOGLE_CSE_API_KEY", "GOOGLE_CSE_ENGINE_ID"]


def validar_google_cse(config: dict) -> None:
    """Verifica que las claves de Google Custom Search estén presentes.

    Solo llamar desde módulos que realmente las necesiten (descubrir.py).
    """
    faltantes = [k for k in GOOGLE_CSE_REQUERIDAS if not config.get(k)]
    if faltantes:
        raise ConfigError(
            f"Faltan claves de Google Custom Search: {', '.join(faltantes)}. "
            "Configúralas en config/.env (ver instrucciones en plan 2)."
        )


def validar_brave(config: dict) -> None:
    """Verifica que la clave de Brave Search esté presente.

    Solo llamar desde módulos que realmente la necesiten (web_finder, enriquecer).
    """
    if not config.get("BRAVE_SEARCH_API_KEY"):
        raise ConfigError(
            "Falta BRAVE_SEARCH_API_KEY. Crea una cuenta en https://api.search.brave.com "
            "y configúrala en config/.env (ver Tarea 0 del plan 3)."
        )
