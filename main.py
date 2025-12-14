import os
import logging
from flask import Flask

from src.server import server
from src.utils.constants import NETWORK_PATH
from src.utils.utils import get_local_ip

logging.getLogger("werkzeug").disabled = True


def create_app():
    print(f" > SERVER RUNNING ON: http://{get_local_ip()}:5000")
    app = Flask(
        __name__,
        template_folder=os.path.join(NETWORK_PATH, "templates"),
        static_folder=os.path.join(NETWORK_PATH, "static"),
    )

    db = server.Database()
    backend = server.Server(db=db, app=app)
    app.backend = backend
    return app


# Gunicorn entry point
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0")
