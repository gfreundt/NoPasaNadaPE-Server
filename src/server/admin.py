from flask import request, jsonify
import uuid

from src.utils.constants import INTERNAL_AUTH_TOKEN
from src.utils.utils import hash_text


def main(self):

    # informacion de la solicitud
    token = request.args.get("token")
    solicitud = request.args.get("solicitud").lower()
    correo = request.args.get("correo")

    # error en token de seguridad
    if token != INTERNAL_AUTH_TOKEN:
        respuesta_mensaje = "Error en Token de Autorizacion."
        respuesta_codigo = 401

    # solicitud de generar nuevo password
    elif solicitud == "nuevo_password":

        # generar un simple password de 6 caracteres alfanumericos y convertirlo en hash
        nuevo_password = uuid.uuid4().hex[:6]
        nuevo_password_hash = hash_text(nuevo_password)

        # actualizar base de datos con password nuevo y resetear intentos de login
        cmd = "UPDATE InfoMiembros SET NextLoginAllowed = NULL, CountFailedLogins = 0, Password = ? WHERE Correo = ?"
        self.db.cursor.execute(cmd, (nuevo_password_hash, correo))
        self.db.conn.commit()

        respuesta_mensaje = f"Nuevo Password: {nuevo_password}"
        respuesta_codigo = 200

    # error generico para casuisticas no especificas
    else:
        respuesta_mensaje = "Error en solicitud."
        respuesta_codigo = 400

    return jsonify(respuesta_mensaje), respuesta_codigo
