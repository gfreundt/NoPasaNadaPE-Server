import os
import logging
from flask import Flask

from src.server import server
from src.dashboard import dashboard
from src.utils.constants import NETWORK_PATH
from security.keys import DASHBOARD_URL
from src.utils.utils import get_local_ip, is_master_worker

logging.getLogger("werkzeug").disabled = True


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

    backend = server.Server(db=db, app=app, dash=dash)
    app.backend = backend
    return app


# Gunicorn entry point
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0")
