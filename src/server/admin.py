from flask import request, jsonify
import uuid

from src.utils.constants import INTERNAL_AUTH_TOKEN
from src.utils.utils import hash_text


def main(self):

    token = request.args.get("token")
    solicitud = (request.args.get("solicitud") or "").lower()
    correo = request.args.get("correo")

    # 1) Validate security token
    if token != INTERNAL_AUTH_TOKEN:
        return jsonify("Error en Token de Autorizacion."), 401

    # 2) Request for new password
    if solicitud == "nuevo_password":

        # generate 6-char alphanumeric password
        nuevo_password = uuid.uuid4().hex[:6]
        nuevo_password_hash = hash_text(nuevo_password)

        # update database
        cursor = self.db.cursor()
        conn = self.db.conn
        cmd = """
            UPDATE InfoMiembros
            SET NextLoginAllowed = NULL,
                CountFailedLogins = 0,
                Password = ?
            WHERE Correo = ?
        """
        cursor.execute(cmd, (nuevo_password_hash, correo))
        conn.commit()

        return jsonify(f"Nuevo Password: {nuevo_password}"), 200

    # 3) fallback for unsupported actions
    return jsonify("Error en solicitud."), 400
