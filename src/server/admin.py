from flask import request, jsonify
import uuid

from security.keys import INTERNAL_AUTH_TOKEN
from src.utils.utils import hash_text


def main(self):

    token = request.args.get("token")
    solicitud = (request.args.get("solicitud") or "").lower()
    correo = request.args.get("correo")

    if token != INTERNAL_AUTH_TOKEN:
        return jsonify("Error en Token de Autorizacion."), 401

    cursor = self.db.cursor()
    conn = self.db.conn

    if solicitud == "nuevo_password":

        # generate 6-char alphanumeric password
        nuevo_password = uuid.uuid4().hex[:6]
        nuevo_password_hash = hash_text(nuevo_password)

        # update database

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

    if solicitud == "kill":

        # borra placas asociadas con correo / usuario
        cmd = "UPDATE InfoPlacas SET IdMember_FK = 0 WHERE IdMember_FK IN (SELECT IdMember FROM Infomiembros WHERE Correo = ?)"
        cursor.execute(cmd, (correo,))

        # borra subscripcion de correo / usuario
        cmd = "DELETE FROM InfoMiembros WHERE Correo = ?"
        cursor.execute(cmd, (correo,))

        # borra activacion de correo / usuario
        cmd = "DELETE FROM InfoClientesAutorizados WHERE Correo = ?"
        cursor.execute(cmd, (correo,))

        conn.commit()
        return jsonify(f"Kill: {correo}"), 200

    if solicitud == "vacuum":

        # ajusta el tamano de la base de datos (proceso pesado)
        cursor.execute("VACUUM")
        conn.commit()

    if solicitud == "sunarp_manual":
        cursor.execute(
            """SELECT Placa FROM InfoPlacas
                WHERE IdMember_FK != 0
                    AND
                Placa NOT IN (SELECT PlacaValidate FROM DataSunarpFichas)
            """
        )

        return jsonify([i["Placa"] for i in cursor.fetchall()]), 200

    # 3) fallback for unsupported actions
    return jsonify("Error en solicitud."), 400
