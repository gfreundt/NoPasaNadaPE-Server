import os
import fcntl
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
from flask import Flask

from src.utils.constants import NETWORK_PATH
from src.utils.utils import get_local_ip
from src.server import cron, database, settings


def create_app():
    print(f" > SERVER: http://{get_local_ip()}:5000/")

    # define la aplicacion de flask
    app = Flask(
        __name__,
        template_folder=os.path.join(NETWORK_PATH, "templates"),
        static_folder=os.path.join(NETWORK_PATH, "static"),
    )

    # configura parametros de Flask
    settings.configurar_flask(app)

    # configura rutas de Flask y las funciones asociandas
    settings.definir_rutas(app)

    # configuracion de OAuth para login con apps de terceros
    settings.configurar_oauth(app)

    return app


def iniciar_base_de_datos():
    # inicia la base de datos
    db = database.Database()
    db._lock_file_handle = None

    return db


def inicia_cron(db):
    """
    Funcion utilizada para darle status de "master" solamente al primer worker de Gunicorn.
    Intenta acceder a archivo y si esta siendo utilizado no da el status de master al worker
    En caso sea "master" activa cron.py
    """

    lock_path = os.path.join(NETWORK_PATH, "static", "dashboard_init.lock")
    db._lock_file_handle = open(lock_path, "a")

    try:
        fcntl.flock(db._lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cron.main(db)

    except (OSError, BlockingIOError):
        db._lock_file_handle.close()
        db._lock_file_handle = None
        return


def inicia_logger():
    # crea logger root
    logger = logging.getLogger()

    # necesario para Gunicorn: limitar a un solo worker creando un handler
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = ConcurrentRotatingFileHandler(
            os.path.join(NETWORK_PATH, "app.log"), "a", 10 * 1024 * 1024, 3
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

    # reducir logging de apps de terceros
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # Flask server
    logging.getLogger("seleniumwire").setLevel(logging.WARNING)  # Selenium Wire


# ------------ Gunicorn: punto de entrada
inicia_logger()
db = iniciar_base_de_datos()
app = create_app()
app.db = db
inicia_cron(db)

# ------------ Punto de entrada si se corre manualmente
if __name__ == "__main__":
    app.run(host="0.0.0.0")
