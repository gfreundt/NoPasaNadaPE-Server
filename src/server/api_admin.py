import os
from flask import current_app, request, jsonify
import uuid
import logging
from pprint import pformat, pprint

from security.keys import INTERNAL_AUTH_TOKEN
from src.utils.utils import hash_text, NETWORK_PATH
from src.server import do_updates, prueba_scrapers
from src.updates import extrae_data_terceros, datos_actualizar, do_actualizar


logger = logging.getLogger(__name__)


def main():

    try:
        db = current_app.db

        logger.info("Endpoint: admin accesado")

        token = request.args.get("token")
        solicitud = (request.args.get("solicitud") or "").lower()
        correo = request.args.get("correo")
        payload = request.get_json(silent=True) or {}

        if token != INTERNAL_AUTH_TOKEN:
            logger.warning("Acceso no autorizado. Error en Token de Autorizacion.")
            return jsonify("Error en Token de Autorizacion."), 401

        cursor = db.cursor()
        conn = db.conn

        if solicitud == "nuevo_password":
            logger.info(f"Generando nuevo password para: {correo}")

            # generate 6-char alphanumeric password
            nuevo_password = uuid.uuid4().hex[:6]

            # update database
            cmd = """
                    UPDATE InfoMiembros
                    SET NextLoginAllowed = NULL,
                        CountFailedLogins = 0,
                        Password = ?
                    WHERE Correo = ?
                    """
            cursor.execute(cmd, (hash_text(nuevo_password), correo))
            conn.commit()

            return jsonify(f"Nuevo Password: {nuevo_password}"), 200

        if solicitud == "kill":
            logger.info(f"Eliminando usuario y datos asociados (KILL): {correo}")

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
            logger.info("Iniciando VACUUM de la base de datos.")
            cursor.execute("VACUUM")
            conn.commit()

        if solicitud == "get_logger":
            logger.info("Generando logs del sistema.")
            n = payload.get("limit", 500)
            with open(os.path.join(NETWORK_PATH, "app.log"), "r") as f:
                logs = f.readlines()[-n:]
            return jsonify(logs), 200

        if solicitud == "manual_upload":
            logger.info("Upload manual iniciado.")
            do_updates.main(db, payload)
            return jsonify("Actualizado."), 200

        if solicitud == "get_sunarp":
            logger.info("Generando lista de pendientes para SUNARP.")
            cmd = """   SELECT Placa FROM InfoPlacas
                        WHERE LastUpdateSunarpFichas = '2020-01-01'"""
            cursor.execute(cmd)
            faltan = {"DataSunarpFichas": [i["Placa"] for i in cursor.fetchall()]}
            return jsonify(faltan), 200

        if solicitud == "get_faltan":
            # deprecated
            logger.info("Generando lista de faltantes para MTC.")
            cmd = """   SELECT DocTipo, DocNum, Correo FROM InfoMiembros
                        WHERE IdMember NOT IN (SELECT IdMember_FK FROM DataMtcBrevetes)"""
            cursor.execute(cmd)
            faltan = {"DataMtcBrevetes": [tuple(i) for i in cursor.fetchall()]}

            cmd = """   SELECT DocTipo, DocNum, Correo FROM InfoMiembros
                        WHERE IdMember NOT IN (SELECT IdMember_FK FROM DataMtcRecordsConductores)"""
            cursor.execute(cmd)
            faltan.update(
                {"DataMtcRecordsConductores": [tuple(i) for i in cursor.fetchall()]}
            )
            cmd = """   SELECT
                        T1.DocTipo,
                        T1.DocNum,
                        T2.Placa,
                        T1.Correo
                    FROM
                        InfoMiembros AS T1  -- T1 is InfoMiembros
                    INNER JOIN
                        InfoPlacas AS T2    -- T2 is InfoPlacas
                    ON
                        T1.IdMember = T2.IdMember_FK
                    WHERE
                        T2.Placa NOT IN (SELECT PlacaValidate FROM DataMtcRevisionesTecnicas)
                        AND T2.IdMember_FK != 0;"""

            cursor.execute(cmd)
            faltan.update(
                {"DataMtcRevisionesTecnicas": [tuple(i) for i in cursor.fetchall()]}
            )

            return jsonify(faltan), 200

        if solicitud == "force_update":
            id_member = payload.get("id_member")
            logger.info(
                f"Iniciando actualización forzada desde Admin. ID Member: {id_member}"
            )

            try:
                datos = datos_actualizar.get_datos_un_miembro(
                    db=db, id_member=id_member
                )
                extrae_data_terceros.main(db, datos)
                return jsonify(
                    f"Actualizacion Forzada Completa de IdMember: {id_member}"
                ), 200

            except Exception as e:
                logger.error(
                    f"Error al forzar actualización de IdMember: {id_member}, Error: {e}"
                )
                return jsonify(
                    f"Error al forzar actualización de IdMember: {id_member}"
                ), 500

        if solicitud == "prueba_scrapers":
            try:
                prueba_scrapers.main()
                return jsonify(
                    "Prueba de Scrapers Completa. Resultados por Correo."
                ), 200
            except Exception as e:
                return jsonify("No se lanzo prueba scrapers."), 500

        if solicitud == "trigger_alertas":
            try:
                do_actualizar.main(db, "alertas")
                return jsonify("Proceso de Alertas Gatillado"), 200
            except Exception as e:
                return jsonify(f"No se lanzo alertas: {e}"), 500

        if solicitud == "trigger_boletines":
            try:
                do_actualizar.main(db, "boletines")
                return jsonify("Proceso de Boletines Gatillado."), 200
            except Exception as e:
                return jsonify(f"No se lanzo boletines: {e}"), 500

        # solicitud no reconocida
        logger.warning("Solicitud no reconocida.")
        return jsonify({}), 400

    except Exception as e:
        print(e)
