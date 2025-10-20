def update_table(db_cursor):
    """Creates table with all members with SOAT, REVTEC, SUTRAN, SATMUL, BREVETE or SATIMP
    expired or expiring within 30 days."""

    _cmd = """  DELETE FROM _expira30dias;

                -- Incluir usuarios que tienen multas vigentes o documentos por vencer dentro de 30 dias o ya vencidos
                INSERT INTO _expira30dias (IdMember, FechaHasta, TipoAlerta)
                SELECT 
                    i.IdMember,
                    d.FechaHasta,
                    d.TipoAlerta
                FROM 
                    InfoMiembros i
                JOIN (
                    -- BREVETE alerts
                    SELECT 
                        IdMember_FK, 
                        FechaHasta, 
                        'BREVETE' AS TipoAlerta
                    FROM DataMtcBrevetes
                    WHERE DATE('now', 'localtime', '+30 days') >= FechaHasta
                    OR DATE('now', 'localtime') = FechaHasta

                    UNION

                    -- SATIMP alerts
                    SELECT 
                        b.IdMember_FK, 
                        a.FechaHasta, 
                        'SATIMP' AS TipoAlerta
                    FROM DataSatImpuestosDeudas a
                    JOIN DataSatImpuestosCodigos b ON a.Codigo = b.Codigo
                    WHERE DATE('now', 'localtime', '+30 days') >= a.FechaHasta
                ) d
                ON i.IdMember = d.IdMember_FK;



                -- Incluir placas que tienen multas vigentes o documentos por vencer dentro de 30 dias o ya vencidos
                INSERT INTO _expira30dias (IdMember,  Placa, FechaHasta, TipoAlerta)
                    SELECT IdMember, Placa, FechaHasta, TipoAlerta FROM InfoMiembros
                        JOIN (
                            SELECT * FROM InfoPlacas 
                                JOIN (
                            SELECT PlacaValidate, FechaHasta, "SOAT" AS TipoAlerta FROM DataApesegSoats
                                WHERE DATE('now', 'localtime', '+30 days') >= FechaHasta
                                UNION
                            SELECT PlacaValidate, FechaHasta, "REVTEC" FROM DataMtcRevisionesTecnicas
                                WHERE DATE('now', 'localtime', '+30 days') >= FechaHasta
                                UNION 
                            SELECT PlacaValidate, "", "SUTRAN" FROM DataSutranMultas
                                UNION 
                            SELECT PlacaValidate, "", "SATMUL" FROM DataSatMultas)
                                ON Placa = PlacaValidate)
                        ON IdMember = IdMember_FK;

                                    
                -- Crear un flag de si esta por vencer o ya vencio     
                UPDATE _expira30dias SET Vencido = 0;
                UPDATE _expira30dias SET Vencido = 1 WHERE FechaHasta < DATE('now', 'localtime');
            """

    db_cursor.executescript(_cmd)
