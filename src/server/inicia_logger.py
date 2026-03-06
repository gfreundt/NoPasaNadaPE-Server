import os
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler

from src.utils.constants import LOG_PATH


def main():
    """
    Inicia dos loggers:
    - app.log con nivel INFO (tamaño 8Gb, maximo 3 archivos)
    - debug.log con nivel DEBUG (tamaño 8Gb, maximo 4 archivos)
    Usa ConcurrentRotatingFileHandler para que todos los workers puedan escribir al mismo archivo sin problemas de concurrencia.
    """

    logger = logging.getLogger()

    # crea el path en caso no exista
    os.makedirs(LOG_PATH, exist_ok=True)

    # Gunicorn: limitar a un solo worker creando un handler
    if not logger.handlers:
        # definir nivel base, luego override por cada handler
        logger.setLevel(logging.DEBUG)

        # definir tamaño y formato del texto del log
        log_size = 8 * 1024 * 1024
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # definir app.log de nivel INFO
        info_handler = ConcurrentRotatingFileHandler(
            os.path.join(LOG_PATH, "app.log"),
            mode="a",
            maxBytes=log_size,
            backupCount=3,
        )
        info_handler.setFormatter(formatter)
        info_handler.setLevel(logging.INFO)

        # definir debug.log de nivel DEBUG
        debug_handler = ConcurrentRotatingFileHandler(
            os.path.join(LOG_PATH, "debug.log"),
            mode="a",
            maxBytes=log_size,
            backupCount=4,
        )
        debug_handler.setFormatter(formatter)
        debug_handler.setLevel(logging.DEBUG)

        # agregar handler a logger y que no propaguen
        logger.addHandler(info_handler)
        logger.addHandler(debug_handler)
        logger.propagate = False

        # primer log para visualmente marcar el reinicio del sistema
        logger.info("-" * 25 + " REINICIO " + "-" * 25)

    # reducir logging de apps de terceros
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # Flask server
    logging.getLogger("seleniumwire").setLevel(logging.WARNING)  # Selenium Wire
