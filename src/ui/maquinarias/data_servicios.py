def generar(db, correo):

    cursor = db.cursor()

    # obtener informacion de miembro y placa, almacenar en variables
    cursor.execute(
        "SELECT IdMember, LastUpdateMtcBrevetes, LastUpdateMtcRecordsConductores, LastUpdateSatImpuestosCodigos FROM InfoMiembros WHERE Correo = ? LIMIT 1",
        (correo,),
    )
    data_miembro = cursor.fetchone()
    id_member = data_miembro["IdMember"]

    desconocido = {
        "Estado": "Sin Informacion",
        "FechaHasta": "",
        "FechaHastaDias": "",
        "LastUpdate": "",
        "LastUpdateDias": "",
    }
    vencimientos = {}
    multas = {}
    descargas = {}

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
                LastUpdate
                FROM
                DataMtcRecordsConductores
                WHERE
                IdMember_FK = {id_member}
            """
    cursor.execute(cmd)
    descargas.update({"record_conductor": [i for i in cursor.fetchall()]})

    # descargas = {
    #     "soat_certificados": [
    #         "ABC123",  # Example Plate 1
    #         "ZXC987",  # Example Plate 2
    #         "QWE456",  # Example Plate 3
    #     ],
    #     "sunarp_certificados": [
    #         "ABC123",  # Example Plate 1
    #         "FGH789",  # Example Plate 2
    #     ],
    #     "record_conductor": [{"documento": "DNI-12345678"}],  # Max 1 item (or none)
    # }

    # Example of an empty structure to test "No hay..." messages:
    # descargas = {
    #     "soat_certificados": [],
    #     "sunarp_certificados": [],
    #     "record_conductor": [],
    # }

    return {
        "vencimientos": vencimientos,
        "multas": multas,
        "descargas": descargas,
    }
