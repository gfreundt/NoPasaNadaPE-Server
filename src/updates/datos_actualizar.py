# datos_actualizar.py
from src.updates import configuracion_plazos

ULTIMA_ACTUALIZACION_HORAS = 48


def alertas(db_cursor):
    """
    Genera requerimientos de actualización basados en las reglas de configuracion_plazos.
    """

    # Generamos los fragmentos SQL dinámicamente
    sql_soat = configuracion_plazos.generar_sql_condicion("s.FechaHasta", "SOAT")
    sql_revtec = configuracion_plazos.generar_sql_condicion("r.FechaHasta", "REVTEC")
    sql_brevete = configuracion_plazos.generar_sql_condicion("b.FechaHasta", "BREVETE")
    sql_satimp = configuracion_plazos.generar_sql_condicion("d.FechaHasta", "SATIMP")

    query = f"""
    WITH RecentAlerts AS (
        SELECT IdMember_FK 
        FROM StatusMensajesEnviados
        WHERE DATE(FechaEnvio) > DATE('now', 'localtime', '-1 day') 
        AND TipoMensaje = 'Alerta'
    )
    -- 1. SOAT
    SELECT 'SOAT' as Tipo, p.IdMember_FK, NULL as DocTipo, NULL as DocNum, s.PlacaValidate as Placa
    FROM DataApesegSoats s
    JOIN InfoPlacas p ON p.Placa = s.PlacaValidate
    WHERE p.IdMember_FK > 0
      AND p.IdMember_FK NOT IN (SELECT IdMember_FK FROM RecentAlerts)
      AND p.LastUpdateApesegSoats < datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      AND {sql_soat}
    
    UNION ALL
    
    -- 2. REVTEC
    SELECT 'REVTEC', p.IdMember_FK, NULL, NULL, r.PlacaValidate
    FROM DataMtcRevisionesTecnicas r
    JOIN InfoPlacas p ON p.Placa = r.PlacaValidate
    WHERE p.IdMember_FK > 0
      AND p.IdMember_FK NOT IN (SELECT IdMember_FK FROM RecentAlerts)
      AND p.LastUpdateMtcRevisionesTecnicas < datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      AND {sql_revtec}

    UNION ALL
    
    -- 3. BREVETE
    SELECT 'BREVETE', m.IdMember, m.DocTipo, m.DocNum, NULL
    FROM DataMtcBrevetes b
    JOIN InfoMiembros m ON m.IdMember = b.IdMember_FK
    WHERE m.IdMember > 0
      AND m.IdMember NOT IN (SELECT IdMember_FK FROM RecentAlerts)
      AND m.LastUpdateMtcBrevetes < datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      AND {sql_brevete}

    UNION ALL
    
    -- 4. SATIMP
    SELECT 'SATIMP', m.IdMember, m.DocTipo, m.DocNum, NULL
    FROM DataSatImpuestosDeudas d
    JOIN DataSatImpuestosCodigos c ON d.Codigo = c.Codigo
    JOIN InfoMiembros m ON m.IdMember = c.IdMember_FK
    WHERE m.IdMember > 0
      AND m.IdMember NOT IN (SELECT IdMember_FK FROM RecentAlerts)
      AND {sql_satimp}
    """

    db_cursor.execute(query)
    results = db_cursor.fetchall()

    upd = {"brevetes": [], "soats": [], "revtecs": [], "satimps": []}

    for row in results:
        tipo = row[0]
        if tipo == "BREVETE":
            upd["brevetes"].append((row[1], row[2], row[3]))
        elif tipo == "SOAT":
            upd["soats"].append(row[4])
        elif tipo == "REVTEC":
            upd["revtecs"].append(row[4])
        elif tipo == "SATIMP":
            upd["satimps"].append((row[1], row[2], row[3]))

    return {k: list(set(v)) for k, v in upd.items()}


def boletines(db_cursor):
    """
    Genera requerimientos de actualización para boletines.
    """
    SUNARP_DAYS = 120

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
    SELECT 'brevetes' AS KeyName, u.IdMember AS IdMember_FK, u.DocTipo, u.DocNum, NULL AS Placa
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
    SELECT 'soats', NULL, NULL, NULL, p.Placa
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
    SELECT 'revtecs', NULL, NULL, NULL, p.Placa
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
    SELECT 'sunarps', NULL, NULL, NULL, p.Placa
    FROM TargetPlacas p
    WHERE p.Placa NOT IN (
          SELECT Placa FROM InfoPlacas 
          WHERE LastUpdateSunarpFichas >= datetime('now','localtime', '-{SUNARP_DAYS} days')
      )

    UNION ALL

    -- 5. SATIMPS (Usa TargetUsers)
    SELECT 'satimps', u.IdMember, u.DocTipo, u.DocNum, NULL
    FROM TargetUsers u
    WHERE u.IdMember NOT IN (
          SELECT IdMember FROM InfoMiembros 
          WHERE LastUpdateSatImpuestosCodigos >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 6. SATMULS (Usa TargetPlacas)
    SELECT 'satmuls', NULL, NULL, NULL, p.Placa
    FROM TargetPlacas p
    WHERE p.Placa NOT IN (
          SELECT Placa FROM InfoPlacas 
          WHERE LastUpdateSatMultas >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 7. SUTRANS (Usa TargetPlacas)
    SELECT 'sutrans', NULL, NULL, NULL, p.Placa
    FROM TargetPlacas p
    WHERE p.Placa NOT IN (
          SELECT Placa FROM InfoPlacas 
          WHERE LastUpdateSutranMultas >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 8. RECVEHIC (Usa TargetUsers)
    SELECT 'recvehic', u.IdMember, u.DocTipo, u.DocNum, NULL
    FROM TargetUsers u
    WHERE u.DocTipo = 'DNI'
      AND u.IdMember NOT IN (
          SELECT IdMember FROM InfoMiembros 
          WHERE LastUpdateMtcRecordsConductores >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    UNION ALL

    -- 9. CAMUL (Usa TargetPlacas)
    SELECT 'calmul', NULL, NULL, NULL, p.Placa
    FROM TargetPlacas p
    WHERE p.Placa NOT IN (
          SELECT Placa FROM InfoPlacas 
          WHERE LastUpdateCallaoMultas >= datetime('now','localtime', '-{ULTIMA_ACTUALIZACION_HORAS} hours')
      )

    """

    db_cursor.execute(query)
    results = db_cursor.fetchall()

    # Inicializar diccionario
    upd = {
        "brevetes": [],
        "soats": [],
        "revtecs": [],
        "sunarps": [],
        "satimps": [],
        "satmuls": [],
        "sutrans": [],
        "recvehic": [],
        "calmul": [],
    }

    for row in results:
        key = row[0]
        if key in ["soats", "revtecs", "sunarps", "satmuls", "sutrans", "calmul"]:
            upd[key].append(row[4])
        else:
            upd[key].append((row[1], row[2], row[3]))

    # Retornar listas únicas
    return {i: list(set(j)) for i, j in upd.items()}
