import os
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
from flask import Flask
from src.utils.constants import NETWORK_PATH
from src.utils.utils import get_local_ip, soy_master_worker
from src.server import server
from src.dashboard import cron
# from src.dashboard import dashboard


def create_app():
    print(f" > SERVER: http://{get_local_ip()}:5000/")

    # define la aplicacion de flask
    app = Flask(
        __name__,
        template_folder=os.path.join(NETWORK_PATH, "templates"),
        static_folder=os.path.join(NETWORK_PATH, "static"),
    )

    # configura las rutas y las funciones del backend
    server.Server(db=db, app=app)

    return app


def iniciar_base_de_datos():
    # inicia la base de datos
    db = server.Database()
    db._lock_file_handle = None
    return db


def inicia_cron(db):
    # iniciar cron solamente en el caso que esta instancia sea "master"
    if soy_master_worker(db):
        cron.main(db)


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


# Gunicorn punto de entrada
inicia_logger()
db = iniciar_base_de_datos()
app = create_app()
inicia_cron(db)

# punto de entrada si se corre manualmente
if __name__ == "__main__":
    app.run(host="0.0.0.0")
