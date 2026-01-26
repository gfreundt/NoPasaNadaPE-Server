# necesitan_mensajes.py
from src.updates import configuracion_plazos


def alertas(db_cursor):
    """
    Recupera una lista de miembros/placas que requieren una alerta.
    Usa la lógica centralizada en configuracion_plazos.py.
    """

    # Generamos los fragmentos SQL.
    # Aquí no usamos alias de tabla (como 's.') porque los SELECTS son directos sobre la tabla origen.
    sql_soat = configuracion_plazos.generar_sql_condicion("FechaHasta", "SOAT")
    sql_revtec = configuracion_plazos.generar_sql_condicion("FechaHasta", "REVTEC")
    sql_brevete = configuracion_plazos.generar_sql_condicion("FechaHasta", "BREVETE")
    sql_satimp = configuracion_plazos.generar_sql_condicion("a.FechaHasta", "SATIMP")

    cmd = f"""
        WITH RecentAlerts AS (
            -- Get IDs of members who already received an alert in the last 25 hours
            SELECT IdMember
            FROM StatusMensajesEnviados
            WHERE DATE(FechaEnvio) = DATE('now', 'localtime') 
            AND TipoMensaje = 'ALERTA'
        ),
        Alerts AS (
            -- 1. SOAT
            SELECT 
                FechaHasta, 'SOAT' AS TipoAlerta, PlacaValidate AS Placa, 
                (SELECT IdMember_FK FROM InfoPlacas WHERE Placa = PlacaValidate) AS IdMember_FK,
                NULL AS DocTipo, NULL AS DocNum
            FROM DataApesegSoats c
            WHERE {sql_soat}
            AND c.LastUpdate < DATETIME('now', 'localtime', '-23 hours')
            AND IdMember_FK NOT IN (SELECT IdMember FROM RecentAlerts)

            UNION ALL

            -- 2. REVISION TECNICA (REVTEC)
            SELECT 
                FechaHasta, 'REVTEC' AS TipoAlerta, PlacaValidate AS Placa, 
                (SELECT IdMember_FK FROM InfoPlacas WHERE Placa = PlacaValidate) AS IdMember_FK,
                NULL AS DocTipo, NULL AS DocNum
            FROM DataMtcRevisionesTecnicas d
            WHERE {sql_revtec}
            AND d.LastUpdate < DATETIME('now', 'localtime', '-23 hours')
            AND IdMember_FK NOT IN (SELECT IdMember FROM RecentAlerts)

            UNION ALL

            -- 3. BREVETE
            SELECT 
                FechaHasta, 'BREVETE' AS TipoAlerta, NULL AS Placa, IdMember_FK,
                (SELECT DocTipo FROM InfoMiembros WHERE IdMember = IdMember_FK) AS DocTipo,
                (SELECT DocNum FROM InfoMiembros WHERE IdMember = IdMember_FK) AS DocNum
            FROM DataMtcBrevetes e
            WHERE {sql_brevete}
            AND e.LastUpdate < DATETIME('now', 'localtime', '-23 hours')
            AND IdMember_FK NOT IN (SELECT IdMember FROM RecentAlerts)

            UNION ALL

            -- 4. SAT IMPUESTOS (SATIMP)
            SELECT 
                a.FechaHasta, 'SATIMP' AS TipoAlerta, NULL AS Placa, IdMember_FK,
                (SELECT DocTipo FROM InfoMiembros WHERE IdMember = IdMember_FK) AS DocTipo,
                (SELECT DocNum FROM InfoMiembros WHERE IdMember = IdMember_FK) AS DocNum
            FROM DataSatImpuestosDeudas a
            JOIN DataSatImpuestosCodigos b ON a.Codigo = b.Codigo
            WHERE {sql_satimp}
            AND a.LastUpdate < DATETIME('now', 'localtime', '-23 hours')
            AND IdMember_FK NOT IN (SELECT IdMember FROM RecentAlerts)
        )

        SELECT 
            IdMember_FK AS IdMember,
            TipoAlerta,
            CASE 
                WHEN DATE('now', 'localtime') >= FechaHasta THEN 1 
                ELSE 0 
            END AS Vencido,
            FechaHasta, 
            Placa, 
            DocTipo, 
            DocNum
        FROM Alerts
        WHERE IdMember_FK IS NOT NULL 
        AND IdMember_FK != 0;
    """

    db_cursor.execute(cmd)
    rows = db_cursor.fetchall()

    if db_cursor.description:
        columns = [col[0] for col in db_cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
    else:
        results = []

    print("@@@@@@@@", results)
    return results


def boletines(db_cursor):
    """
    Recupera una lista de diccionarios con los usuarios que requieren el boletín mensual.
    """

    cmd = """
    SELECT IdMember, DocTipo, DocNum, Correo
        FROM InfoMiembros 
        WHERE NextMessageSend <= datetime('now','localtime')
    """

    db_cursor.execute(cmd)
    rows = db_cursor.fetchall()

    if db_cursor.description:
        columns = [col[0] for col in db_cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
    else:
        results = []

    return results
