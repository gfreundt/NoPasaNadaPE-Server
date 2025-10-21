from datetime import datetime as dt
from flask import request, jsonify

from src.utils.constants import EXTERNAL_AUTH_TOKEN


def alta(self):

    token = request.args.get("token")
    correo = request.args.get("correo")
    usuario = request.args.get("usuario")

    if token != EXTERNAL_AUTH_TOKEN:
        response = "Error en Token de Autorizacion."
        code = 401
    elif not correo:
        response = "Lista de correos en blanco o formato equivocado."
        code = 400
    elif not usuario:
        response = "Se debe especificar el nombre del usuario autorizando."
        code = 400
    else:
        self.db.cursor.execute(
            "INSERT INTO InfoAutorizaciones VALUES (?,?,?)",
            (correo, str(dt.now()), usuario),
        )
        response = "Correo autorizado."
        code = 200
        self.db.conn.commit()

    # self.db.cursor.execute("SELECT * FROM InfoAutorizaciones")
    # for i in self.db.cursor.fetchall():
    #     print(dict(i))

    return jsonify(response), code
