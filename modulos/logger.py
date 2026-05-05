import logging
from datetime import date
from pathlib import Path


def obtener_logger(modulo: str, carpeta_logs: Path | str = "data/logs") -> logging.Logger:
    """Devuelve un logger que escribe a un archivo diario y a stdout."""
    carpeta = Path(carpeta_logs)
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"{date.today().isoformat()}.log"

    logger = logging.getLogger(modulo)
    logger.setLevel(logging.INFO)

    if not any(getattr(h, "_cv_archivo", None) == str(archivo) for h in logger.handlers):
        handler = logging.FileHandler(archivo, encoding="utf-8")
        handler._cv_archivo = str(archivo)
        formato = logging.Formatter(f"%(asctime)s [{modulo}] %(levelname)s: %(message)s")
        handler.setFormatter(formato)
        logger.addHandler(handler)

        consola = logging.StreamHandler()
        consola.setFormatter(formato)
        logger.addHandler(consola)

    return logger
