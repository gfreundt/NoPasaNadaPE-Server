import os
import fcntl
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
from flask import Flask

from src.utils.constants import NETWORK_PATH, RUN_PATH, LOG_PATH
from src.server import cron, database, configuraciones, inicia_logger


def inicia_loggerx():
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

    # reducir logging de apps de terceros
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # Flask server
    logging.getLogger("seleniumwire").setLevel(logging.WARNING)  # Selenium Wire

    # primer log para visualmente marcar el reinicio del sistema
    logger.info("-" * 15 + " REINICIO " + "-" * 15)


def crea_flask_app():
    """
    Crea la aplicacion de Flask, configura rutas, funciones y OAuth.
    """

    app = Flask(
        __name__,
        template_folder=os.path.join(NETWORK_PATH, "templates"),
        static_folder=os.path.join(NETWORK_PATH, "static"),
    )

    configuraciones.configurar_flask(app)
    configuraciones.definir_rutas(app)
    configuraciones.configurar_oauth(app)
    return app


def inicia_cron(db):
    """
    Determina si este worker es el "master", intentando acceder a archivo y si esta siendo utilizado.
    En caso sea "master" activa actividades que corren de forma regular (cron.py)
    """

    lock_path = os.path.join(RUN_PATH, "master_worker.lock")
    db._lock_file_handle = open(lock_path, "a")

    # intenta ganar acceso exclusivo al archivo, si no puede es que otro worker ya lo tiene y este no es el master
    try:
        fcntl.flock(db._lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

    except (OSError, BlockingIOError):
        db._lock_file_handle.close()
        db._lock_file_handle = None
        return

    # ejecuta cron en try-except independiente para evitar que errores en cron afecten a la app
    try:
        cron.main(db)
    except KeyboardInterrupt:  # Exception as e:
        logging.error(f"Error en cron: {e}")


# ---------------------------------------
#       GUNICORN: punto de entrada
# ---------------------------------------
inicia_logger.main()
db = database.Database()
app = crea_flask_app()
app.db = db
inicia_cron(db)

# ----------------------------------------------
#       MANUAL: punto de entrada (con DEBUG)
# ----------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
