"""Fixtures compartidas y limpieza entre tests."""
import logging
import pytest


@pytest.fixture(autouse=True)
def _limpiar_handlers_logger():
    """Después de cada test, remueve handlers de todos los loggers para evitar acumulación.

    Esto previene que handlers de un test (apuntando a un tmp_path que ya no existe)
    persistan en el siguiente test cuando se reutilice el mismo nombre de logger.
    """
    yield
    for nombre, logger in list(logging.Logger.manager.loggerDict.items()):
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
