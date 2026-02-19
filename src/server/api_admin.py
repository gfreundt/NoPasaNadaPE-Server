import os
from flask import current_app, request, jsonify
import uuid
import threading
import logging
from pprint import pformat

from security.keys import INTERNAL_AUTH_TOKEN
from src.utils.utils import hash_text, NETWORK_PATH
from src.server import do_updates


logger = logging.getLogger(__name__)


def main():

    db = current_app.db

    logger.info("Endpoint: admin accesado")

    token = request.args.get("token")
    solicitud = (request.args.get("solicitud") or "").lower()
    correo = request.args.get("correo")
    payload = request.get_json()

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
        return
        id_member = payload.get("id_member")
        logger.info(
            f"Iniciando actualización forzada desde Admin. ID Member: {id_member}"
        )

        cursor.execute(
            "SELECT NombreCompleto, DocTipo, DocNum FROM InfoMiembros WHERE IdMember = ?",
            (id_member,),
        )
        data = cursor.fetchone()

        if not data:
            logger.warning(f"ID Member no encontrado: {id_member}")
            return jsonify("ID Member no encontrado."), 404

        # inicio de proceso interno en thread separado
        doc_tipo, doc_num = data["DocTipo"], data["DocNum"]

        cursor.execute(
            "SELECT Placa FROM InfoPlacas WHERE IdMember_FK = ?", (id_member,)
        )
        placas = [i["Placa"] for i in cursor.fetchall()]

        upd = {
            "DataMtcBrevetes": [(id_member, doc_tipo, doc_num)],
            "DataApesegSoats": placas,
            "DataMtcRevisionesTecnicas": placas,
            "DataSatImpuestos": [(id_member, doc_tipo, doc_num)],
            "DataSatMultas": placas,
            "DataSutranMultas": placas,
            "DataMtcRecordsConductores": [(id_member, doc_tipo, doc_num)],
            "DataCallaoMultas": placas,
            "DataSunarpFichas": placas,
        }

        logger.info(f"Datos a actualizar (forzado): \n{pformat(upd)}")

        thread = threading.Thread(target=gather_all.gather_threads, args=(db, upd))
        thread.start()

        return jsonify(f"Lanzado Actualizacion de {data['NombreCompleto']}"), 200

    # solicitud no reconocida
    logger.warning("Solicitud no reconocida.")
    return jsonify({}), 400


def boletineds(cursor):
    """
    Genera requerimientos de actualización para boletines.
    """
    SUNARP_DAYS = 120
    ULTIMA_ACTUALIZACION_HORAS = 48

    # Definimos los CTEs 'TargetUsers' y 'TargetPlacas' al principio.
    query = f"""
    WITH TargetUsers AS (
        SELECT IdMember, DocTipo, DocNum
        FROM InfoMiembros
        WHERE NextMessageSend <= datetime('now','localtime')
    ),
    TargetPlacas AS (
        SELECT p.Placa
        FROM InfoPlacas p
        JOIN TargetUsers u ON u.IdMember = p.IdMember_FK
    )

    -- 1. BREVETES (Usa TargetUsers)
    SELECT 'DataMtcBrevetes' AS KeyName, u.IdMember AS IdMember_FK, u.DocTipo, u.DocNum, NULL AS Placa
    FROM TargetUsers u
    WHERE u.DocTipo = 'DNI'
      AND u.IdMember NOT IN (
          SELECT IdMember_FK FROM DataMtcBrevetes 
          WHERE FechaHasta >= datetime('now','localtime', '+30 days')
      )
      AND u.IdMember NOT IN (
          SELECT IdMember FROM InfoMiembros 
          WHERE LastUpdateMtcBrevetes >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 2. SOATS (Usa TargetPlacas)
    SELECT 'DataApesegSoats', NULL, NULL, NULL, p.Placa
    FROM TargetPlacas p
    WHERE p.Placa NOT IN (
          SELECT PlacaValidate FROM DataApesegSoats 
          WHERE FechaHasta >= datetime('now','localtime', '+15 days')
      )
      AND p.Placa NOT IN (
          SELECT Placa FROM InfoPlacas 
          WHERE LastUpdateApesegSoats >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 3. REVTECS (Usa TargetPlacas)
    SELECT 'DataMtcRevisionesTecnicas', NULL, NULL, NULL, p.Placa
    FROM TargetPlacas p
    WHERE p.Placa NOT IN (
          SELECT PlacaValidate FROM DataMtcRevisionesTecnicas 
          WHERE FechaHasta >= datetime('now','localtime', '+30 days')
      )
      AND p.Placa NOT IN (
          SELECT Placa FROM InfoPlacas 
          WHERE LastUpdateMtcRevisionesTecnicas >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 4. SUNARPS (Usa TargetPlacas)
    SELECT 'DataSunarpFichas', NULL, NULL, NULL, p.Placa
    FROM TargetPlacas p
    WHERE p.Placa NOT IN (
         SELECT Placa FROM InfoPlacas 
         WHERE LastUpdateSunarpFichas >= datetime('now','localtime', '-{SUNARP_DAYS} days')
     )

    UNION ALL

    -- 5. SATIMPS (Usa TargetUsers)
    SELECT 'DataSatImpuestos', u.IdMember, u.DocTipo, u.DocNum, NULL
    FROM TargetUsers u
    WHERE u.IdMember NOT IN (
          SELECT IdMember FROM InfoMiembros 
          WHERE LastUpdateSatImpuestos >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 6. SATMULS (Usa TargetPlacas)
    SELECT 'DataSatMultas', NULL, NULL, NULL, p.Placa
    FROM TargetPlacas p
    WHERE p.Placa NOT IN (
          SELECT Placa FROM InfoPlacas 
          WHERE LastUpdateSatMultas >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 7. SUTRANS (Usa TargetPlacas)
    SELECT 'DataSutranMultas', NULL, NULL, NULL, p.Placa
    FROM TargetPlacas p
    WHERE p.Placa NOT IN (
          SELECT Placa FROM InfoPlacas 
          WHERE LastUpdateSutranMultas >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 8. RECVEHIC (Usa TargetUsers)
    SELECT 'DataMtcRecordsConductores', u.IdMember, u.DocTipo, u.DocNum, NULL
    FROM TargetUsers u
    WHERE u.DocTipo = 'DNI'
      AND u.IdMember NOT IN (
          SELECT IdMember FROM InfoMiembros 
          WHERE LastUpdateMtcRecordsConductores >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 9. CAMUL (Usa TargetPlacas)
    SELECT 'DataCallaoMultas', NULL, NULL, NULL, p.Placa
    FROM TargetPlacas p
    WHERE p.Placa NOT IN (
          SELECT Placa FROM InfoPlacas 
          WHERE LastUpdateCallaoMultas >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    """

    # Inicializar diccionario
    upd = {
        "DataMtcBrevetes": [],
        "DataApesegSoats": [],
        "DataMtcRevisionesTecnicas": [],
        "DataSatImpuestos": [],
        "DataSatMultas": [],
        "DataSutranMultas": [],
        "DataMtcRecordsConductores": [],
        "DataCallaoMultas": [],
        "DataSunarpFichas": [],
    }

    #
    cursor.execute(query)

    for row in cursor.fetchall():
        key = row["KeyName"]
        if key in [
            "DataApesegSoats",
            "DataMtcRevisionesTecnicas",
            "DataSatMultas",
            "DataSutranMultas",
            "DataCallaoMultas",
            "DataSunarpFichas",
        ]:
            upd[key].append(row["Placa"])
        else:
            upd[key].append((row["IdMember_FK"], row["DocTipo"], row["DocNum"]))

    # Retornar listas únicas
    return {i: list(set(j)) for i, j in upd.items()}
