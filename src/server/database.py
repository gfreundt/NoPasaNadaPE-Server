import os
import sqlite3
import logging
from src.utils.constants import DB_NETWORK_PATH


logger = logging.getLogger(__name__)


class Database:
    """
    Crea una clase que permite generar conexiones independientes a la misma base de datos.
    Necesario para trabajar con multiples workers en Gunicorn.
    La conexion es inicializada con Row Factory (acceder a resultado de query como diccionario).
    """

    def __init__(self):
        self.conn = None
        self._pid = None

    def _ensure_conn(self):
        """Asegura que cada worker tenga su propia conexion de SQLite."""
        current_pid = os.getpid()

        if self.conn is None or self._pid != current_pid:
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass

            self.conn = sqlite3.connect(
                DB_NETWORK_PATH,
                check_same_thread=False,
                timeout=5.0,
            )
            self.conn.row_factory = sqlite3.Row
            self._pid = current_pid

    def connection(self):
        self._ensure_conn()
        return self.conn

    def cursor(self):
        self._ensure_conn()
        return self.conn.cursor()

    def commit(self):
        self._ensure_conn()
        self.conn.commit()

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
            self._pid = None
