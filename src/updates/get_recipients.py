def need_alert(db_cursor):
    """creates one table with all the members/placas that require an alert
    which is later used as reference for determining which records to update"""

    cmd = """   
                -- Borrar todo el contenido de la tabla
                DELETE FROM _necesitan_alertas;

                --- Incluir usuarios/placas con documentos en fecha de vencimiento en x dias exactos o 0-3 dias vencido.
                INSERT INTO _necesitan_alertas (FechaHasta, TipoAlerta, Placa, IdMember_FK)
                    SELECT FechaHasta, "SOAT", PlacaValidate, (SELECT IdMember_FK FROM InfoPlacas WHERE Placa = PlacaValidate) FROM DataApesegSoats
                        WHERE 	DATE('now', 'localtime', '+5 days') = FechaHasta
                        OR 		(DATE('now', 'localtime', '0 days') >= FechaHasta
                                    AND DATE('now', 'localtime', '-3 days') <= FechaHasta)
                    UNION
                    SELECT FechaHasta, "REVTEC", PlacaValidate, (SELECT IdMember_FK FROM InfoPlacas WHERE Placa = PlacaValidate) FROM DataMtcRevisionesTecnicas
                        WHERE 	DATE('now', 'localtime', '+15 days') = FechaHasta
                        OR 		DATE('now', 'localtime', '+7 days') = FechaHasta
                        OR 		(DATE('now', 'localtime', '0 days') >= FechaHasta
                                    AND DATE('now', 'localtime', '-3 days') <= FechaHasta);
                    
                INSERT INTO _necesitan_alertas (IdMember_FK, FechaHasta, TipoAlerta, DocTipo, DocNum)
                    SELECT IdMember_FK, FechaHasta, "BREVETE", (SELECT DocTipo FROM InfoMiembros WHERE IdMember = IdMember_FK), (SELECT DocNum FROM InfoMiembros WHERE IdMember = IdMember_FK) FROM DataMtcBrevetes
                        WHERE 	DATE('now', 'localtime', '+30 days') = FechaHasta
                        OR 		DATE('now', 'localtime', '+10 days')= FechaHasta
                        OR 		(DATE('now', 'localtime', '0 days') >= FechaHasta
                                    AND DATE('now', 'localtime', '-3 days') <= FechaHasta)
                    UNION
                    SELECT IdMember_FK, FechaHasta, "SATIMP", (SELECT DocTipo FROM InfoMiembros WHERE IdMember = IdMember_FK), (SELECT DocNum FROM InfoMiembros WHERE IdMember = IdMember_FK)
                        FROM DataSatImpuestosDeudas a
                        JOIN DataSatImpuestosCodigos b ON a.Codigo = b.Codigo
                        WHERE DATE('now', 'localtime', '+10 days') = FechaHasta
                                OR (DATE('now', 'localtime', '0 days') >= FechaHasta
                                   AND DATE('now', 'localtime', '-3 days') <= FechaHasta);

                --- Incluir DNIs con fecha de vencimiento en x dias exactos o 0-3 dias vencido.
                INSERT INTO _necesitan_alertas (IdMember_FK, DocNum, FechaHasta, TipoAlerta)
                    SELECT IdMember, DocNum, FechaHastaDni, "DNI" FROM InfoMiembros
                        WHERE   DATE('now', 'localtime', '+60 days') = FechaHastaDni
                        OR      DATE('now', 'localtime', '+30 days')= FechaHastaDni
                        OR      DATE('now', 'localtime', '+15 days')= FechaHastaDni
                        OR 		(DATE('now', 'localtime', '0 days') >= FechaHastaDni
                                    AND DATE('now', 'localtime', '-3 days') <= FechaHastaDni);

                --- Incluir Pasaportes/Visas con fecha de vencimiento en x dias exactos o 0-3 dias vencido.
                INSERT INTO _necesitan_alertas (IdMember_FK, DocTipo, FechaHasta, TipoAlerta)
                    SELECT IdMember_FK, Pais, FechaHasta, "PASAPORTE/VISA" FROM InfoPasaportesVisas
                        WHERE   DATE('now', 'localtime', '+180 days') = FechaHasta
                        OR      DATE('now', 'localtime', '+90 days')= FechaHasta
                        OR      DATE('now', 'localtime', '+60 days')= FechaHasta
                        OR      DATE('now', 'localtime', '+15 days')= FechaHasta
                        OR 		(DATE('now', 'localtime', '0 days') >= FechaHasta
                                    AND DATE('now', 'localtime', '-3 days') <= FechaHasta);

                --- Eliminar de alertas los registros que no esten asociados a un usuario.
                DELETE FROM _necesitan_alertas WHERE IdMember_FK = 0;

                --- Eliminar de alertas los registros que hayan recibido una alerta ese mismo dia
                DELETE FROM _necesitan_alertas
                    WHERE IdMember_FK IN (
                        SELECT IdMember_FK
                        FROM StatusMensajesEnviados
                            WHERE DATE(FechaEnvio) > DATE('now', 'localtime', '-1 day')
                            AND Tipo = 'Alerta');
                
                --- Poner todos los flags en 0 (no vencido) y cambiar los que estan vencidos a 1
                UPDATE _necesitan_alertas SET Vencido = 0;
                UPDATE _necesitan_alertas SET Vencido = 1 WHERE DATE('now', 'localtime') >= FechaHasta;
            """

    db_cursor.executescript(cmd)


def need_message(db_cursor):
    """creates two tables (docs and placas) with all the members that require a monthly email
    which are later used as reference for determining which records to update"""

    cmd = """
                -- Borrar todo el contenido de la tabla
                DELETE FROM _necesitan_mensajes_usuarios;

                -- Incluir usuarios que deben recibir el siguiente mensaje
                INSERT INTO _necesitan_mensajes_usuarios (IdMember_FK, DocTipo, DocNum, Tipo)
                    SELECT IdMember, DocTipo, DocNum, "R" from InfoMiembros
                    WHERE NextMessageSend <= datetime('now','localtime');
                            
                -- Borrar contenido de tabla secundaria que lista las placas de usarios que necesitan mensajes
                DELETE FROM _necesitan_mensajes_placas;

                -- Incluir placas de usuarios que necesitan mensajes en tabla secundaria 
                INSERT INTO _necesitan_mensajes_placas (Placa)
                    SELECT Placa FROM InfoPlacas
                        WHERE IdMember_FK IN
                            (SELECT IdMember_FK FROM _necesitan_mensajes_usuarios);
            """

    db_cursor.executescript(cmd)
