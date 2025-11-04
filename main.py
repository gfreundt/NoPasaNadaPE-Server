import os
import sqlite3
import logging
import atexit
from flask import Flask

# local imports
from src.server import server
from src.utils.constants import DB_NETWORK_PATH, NETWORK_PATH

logging.getLogger("werkzeug").disabled = True


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(
            DB_NETWORK_PATH, check_same_thread=False, timeout=5.0
        )
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()


def run_at_exit(backend, db):
    print("Running on Empty")
    backend.log(message="Soft Exit", type=1)
    db.conn.close()


db = Database()
app = Flask(
    __name__,
    template_folder=os.path.join(NETWORK_PATH, "templates"),
    static_folder=os.path.join(NETWORK_PATH, "static"),
)
backend = server.Server(db=db, app=app)
atexit.register(run_at_exit, backend, db)

if __name__ == "__main__":
    backend.run()
