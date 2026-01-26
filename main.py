import os
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
from flask import Flask

from src.server import server
from src.dashboard import dashboard
from src.utils.constants import NETWORK_PATH
from security.keys import DASHBOARD_URL
from src.utils.utils import get_local_ip, is_master_worker


def create_app():
    print(f" > SERVER: http://{get_local_ip()}:5000/")

    app = Flask(
        __name__,
        template_folder=os.path.join(NETWORK_PATH, "templates"),
        static_folder=os.path.join(NETWORK_PATH, "static"),
    )

    # inicia la base de datos
    db = server.Database()

    # inicia Dash para todos los workers pero solo uno es considerado "master"
    db._lock_file_handle = None
    dash = dashboard.Dashboard(db=db, soy_master=is_master_worker(db))

    # inicia Server que procesa solicitudes externas
    backend = server.Server(db=db, app=app, dash=dash)
    app.backend = backend

    return app


def set_up_logger():
    # crea logger root
    logger = logging.getLogger()

    # necesario para Gunicorn: limitar a un solo worker crando un handler
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = ConcurrentRotatingFileHandler(
            os.path.join(NETWORK_PATH, "app.log"), "a", 10 * 1024 * 1024, 3
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - [PID %(process)d] - %(name)s - %(levelname)s - %(message)s"
            )
        )
        logger.addHandler(handler)

    # reducir logging de Flask
    logging.getLogger("werkzeug").setLevel(logging.ERROR)


# Gunicorn punto de entrada
set_up_logger()
app = create_app()

# punto de entrada si se corre manualmente
if __name__ == "__main__":
    app.run(host="0.0.0.0")
