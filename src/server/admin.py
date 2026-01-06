from flask import request, jsonify
import uuid

from security.keys import INTERNAL_AUTH_TOKEN
from src.utils.utils import hash_text
from src.server import do_updates


def main(self):

    token = request.args.get("token")
    solicitud = (request.args.get("solicitud") or "").lower()
    correo = request.args.get("correo")
    payload = request.get_json()

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

    if solicitud == "get_pendientes":
        return jsonify(boletines(cursor)), 200

    if solicitud == "manual_upload":
        print(payload)
        do_updates.main(self.db, payload)
        return jsonify("Actualizado."), 200

    # 3) fallback for unsupported actions
    return jsonify("Error en solicitud."), 400


def boletines(cursor):
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
          WHERE LastUpdateSatImpuestosCodigos >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
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
