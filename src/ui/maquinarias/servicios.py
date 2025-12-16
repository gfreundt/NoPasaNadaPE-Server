from datetime import datetime as dt
from flask import render_template, session, redirect, url_for, request


def main(self):

    # respuesta a pings para medir uptime
    if request.method == "HEAD":
        return ("", 200)

    # seguridad: evitar navegacion directa a url
    if session.get("etapa") != "validado":
        return redirect(url_for("maquinarias"))

    # extraer toda la data relevante de la base de datos
    cursor = self.db.cursor()
    servicios = generar_data_servicios(cursor, correo=session["usuario"]["correo"])

    return render_template(
        "ui-maquinarias-mi-cuenta.html",
        servicios=servicios,
    )


def generar_data_servicios(cursor, correo):

    # obtener informacion de miembro y placa, almacenar en variables
    cursor.execute(
        "SELECT IdMember, LastUpdateMtcBrevetes, LastUpdateMtcRecordsConductores, LastUpdateSatImpuestosCodigos FROM InfoMiembros WHERE Correo = ? LIMIT 1",
        (correo,),
    )
    data_miembro = cursor.fetchone()
    id_member = data_miembro["IdMember"]

    cursor.execute("SELECT Placa FROM InfoPlacas WHERE IdMember_FK = ?", (id_member,))
    placas = ", ".join([i["Placa"] for i in cursor.fetchall()])

    # crear variables en blanco para incluir en servicios
    vencimientos = {}
    multas = {}
    descargas = {}
    usuario = {}

    # brevete
    cmd = f""" SELECT
                CASE WHEN FechaHasta > CURRENT_DATE THEN 'Vigente' ELSE 'Vencido' END AS "Estado",
                FechaHasta,
                CAST(julianday(FechaHasta) - julianday(CURRENT_DATE) AS INTEGER) AS "FechaHastaDias",
                LastUpdate,
                CAST(julianday(CURRENT_DATE) - julianday(LastUpdate) AS INTEGER) AS "LastUpdateDias"
                FROM
                DataMtcBrevetes
                WHERE
                IdMember_FK = {id_member}
            """
    cursor.execute(cmd)
    vencimientos.update({"Licencia de Conducir": [dict(i) for i in cursor.fetchall()]})

    # soat
    cmd = f"""  SELECT
                PlacaValidate AS Placa,
                CASE WHEN FechaHasta > CURRENT_DATE THEN 'Vigente' ELSE 'Vencido' END AS "Estado",
                FechaHasta,
                CAST(julianday(FechaHasta) - julianday(CURRENT_DATE) AS INTEGER) AS "FechaHastaDias",
                LastUpdate,
                CAST(julianday(CURRENT_DATE) - julianday(LastUpdate) AS INTEGER) AS "LastUpdateDias"
                FROM
                DataApesegSoats
                WHERE
                PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {id_member})
            """
    cursor.execute(cmd)
    vencimientos.update({"Certificado SOAT": [dict(i) for i in cursor.fetchall()]})

    # revision tecnica
    cmd = f"""  SELECT
                PlacaValidate AS Placa,
                CASE WHEN FechaHasta > CURRENT_DATE THEN 'Vigente' ELSE 'Vencido' END AS "Estado",
                FechaHasta,
                CAST(julianday(FechaHasta) - julianday(CURRENT_DATE) AS INTEGER) AS "FechaHastaDias",
                LastUpdate,
                CAST(julianday(CURRENT_DATE) - julianday(LastUpdate) AS INTEGER) AS "LastUpdateDias"
                FROM
                DataMtcRevisionesTecnicas
                WHERE
                PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {id_member})"""

    cursor.execute(cmd)
    vencimientos.update({"Revision Tecnica": [dict(i) for i in cursor.fetchall()]})

    # impuestos SAT
    cmd = f"""  SELECT
                Codigo,
                CASE WHEN FechaHasta > CURRENT_DATE THEN 'Vigente' ELSE 'Vencido' END AS "Estado",
                FechaHasta,
                CAST(julianday(FechaHasta) - julianday(CURRENT_DATE) AS INTEGER) AS "FechaHastaDias",
                LastUpdate,
                CAST(julianday(CURRENT_DATE) - julianday(LastUpdate) AS INTEGER) AS "LastUpdateDias"
                FROM
                DataSatImpuestosDeudas
                WHERE
                Codigo = (SELECT Codigo FROM DataSatImpuestosCodigos WHERE IdMember_FK = {id_member})
            """
    cursor.execute(cmd)
    vencimientos.update({"SATIMPS": [dict(i) for i in cursor.fetchall()]})

    # multas SAT
    cmd = f"""  SELECT
                PlacaValidate AS Placa, Falta, FechaEmision, Deuda, Estado, LastUpdate
                FROM
                DataSatMultas
                WHERE
                PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {id_member})
            """
    cursor.execute(cmd)
    multas.update({"SATMULS": [dict(i) for i in cursor.fetchall()]})

    # multas SUTRAN
    cmd = f"""  SELECT
                PlacaValidate AS Placa, CodigoInfrac, FechaDoc, Clasificacion, LastUpdate
                FROM
                DataSutranMultas
                WHERE
                PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {id_member})
            """
    cursor.execute(cmd)
    multas.update({"SUTRANS": [dict(i) for i in cursor.fetchall()]})

    # multas CALLAO
    cmd = f"""  SELECT
                PlacaValidate AS Placa, Codigo, FechaInfraccion, TotalInfraccion, TotalBeneficio, ImageBytes, LastUpdate
                FROM
                DataCallaoMultas
                WHERE
                PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {id_member})
            """
    cursor.execute(cmd)
    multas.update({"CALMUL": [dict(i) for i in cursor.fetchall()]})

    # documentos SOAT
    cmd = f"""  SELECT
                PlacaValidate AS Placa, LastUpdate
                FROM
                DataApesegSoats
                WHERE
                PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {id_member})
            """
    cursor.execute(cmd)
    descargas.update({"soat_certificados": [i["Placa"] for i in cursor.fetchall()]})

    # documentos SUNARP
    cmd = f"""  SELECT
                PlacaValidate AS Placa, LastUpdate
                FROM
                DataSunarpFichas
                WHERE
                PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {id_member})
            """
    cursor.execute(cmd)
    descargas.update({"sunarp_fichas": [i["Placa"] for i in cursor.fetchall()]})

    # documentos RECVEHIC
    cmd = f"""  SELECT
                IdMember_FK, LastUpdate
                FROM
                DataMtcRecordsConductores
                WHERE
                IdMember_FK = {id_member}
            """
    cursor.execute(cmd)
    descargas.update(
        {"record_conductor": [i["IdMember_FK"] for i in cursor.fetchall()]}
    )

    # datos de usuario
    cmd = f"""  SELECT
                NombreCompleto
                FROM
                InfoMiembros
                WHERE
                IdMember = {id_member}
                LIMIT 1
            """
    cursor.execute(cmd)
    u = cursor.fetchone()
    usuario.update({"nombre": u["NombreCompleto"]})

    # determinar si hay data en tablas para pasarle al HTML
    control = {
        "tabla_vencimientos": any([len(vencimientos[i]) for i in vencimientos]),
        "tabla_multas": any([len(multas[i]) for i in multas]),
    }

    return {
        "control": control,
        "usuario": usuario,
        "vencimientos": vencimientos,
        "multas": multas,
        "descargas": descargas,
        "placas": placas,
        "ano": dt.strftime(dt.now(), "%Y"),
    }
