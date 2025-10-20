from src.updates import get_recipients


def get_records(db_cursor):

    # update list of recipients
    get_recipients.need_alert(db_cursor)
    get_recipients.need_message(db_cursor)

    # define when is "recently" for latest update
    R_MSGS = 120  # hours
    R_ALRT = 24  # hours
    upd = {}

    # records that have expiration dates within time thresh (unless updated recently)
    upd["brevetes"] = get_records_brevete(db_cursor, thresh=30, HLA=R_MSGS, HLA2=R_ALRT)
    upd["soats"] = get_records_soats(db_cursor, thresh=15, HLA=R_MSGS, HLA2=R_ALRT)
    upd["revtecs"] = get_records_revtecs(db_cursor, thresh=30, HLA=R_MSGS, HLA2=R_ALRT)
    upd["sunarps"] = get_records_sunarps(db_cursor, thresh=120)

    # records that are updated every time an email is sent (unless updated recently)
    upd["satimps"] = get_records_satimps(db_cursor, HLA=R_MSGS)
    upd["satmuls"] = get_records_satmuls(db_cursor, HLA=R_MSGS)
    upd["sutrans"] = get_records_sutrans(db_cursor, HLA=R_MSGS)
    upd["recvehic"] = get_records_recvehic(db_cursor, HLA=R_MSGS)
    upd["jneafils"] = get_records_jneafils(db_cursor, HLA=R_MSGS)
    upd["sunats"] = get_records_sunats(db_cursor, HLA=R_MSGS)
    upd["jnemultas"] = get_records_jnemultas(db_cursor, HLA=R_MSGS)
    upd["osipteles"] = get_records_osipteles(db_cursor, HLA=R_MSGS)

    # return without any duplicates
    return {i: list(set(j)) for i, j in upd.items()}


def get_records_brevete(db_cursor, thresh, HLA, HLA2):
    # condition to update: will get email and (BREVETE expiring within thresh or no BREVETE in db) and only DNI as document and no attempt to update recently
    db_cursor.execute(
        f"""SELECT IdMember_FK, DocTipo, DocNum FROM _necesitan_mensajes_usuarios
                WHERE IdMember_FK
                    NOT IN 
                    (SELECT IdMember_FK FROM DataMtcBrevetes
                        WHERE
                            FechaHasta >= datetime('now','localtime', '+{thresh} days'))
                            AND
                            DocTipo = 'DNI' 
                            AND
                            IdMember_FK
                            NOT IN 
                            (SELECT IdMember FROM InfoMiembros
                                WHERE LastUpdateMtcBrevetes >= datetime('now','localtime', '-{HLA} hours'))
            UNION
            SELECT IdMember_FK, DocTipo, DocNum FROM _necesitan_alertas
                WHERE TipoAlerta = "BREVETE"
                    AND
                        IdMember_FK
                        NOT IN 
                        (SELECT IdMember FROM InfoMiembros
                            WHERE LastUpdateMtcBrevetes >= datetime('now','localtime', '-{HLA2} hours'))
            """
    )
    return [(i["IdMember_FK"], i["DocTipo"], i["DocNum"]) for i in db_cursor.fetchall()]


def get_records_soats(db_cursor, thresh, HLA, HLA2):
    # condition to update: will get email and (SOAT expiring within thresh or no SOAT in db) and no attempt to update recently
    db_cursor.execute(
        f"""SELECT Placa FROM _necesitan_mensajes_placas
                WHERE Placa
                    NOT IN 
	                (SELECT PlacaValidate FROM DataApesegSoats
		                WHERE
                            FechaHasta >= datetime('now','localtime', '+{thresh} days'))
                            AND
                            Placa
                            NOT IN 
			                (SELECT Placa FROM InfoPlacas
		                        WHERE LastUpdateApesegSoats >= datetime('now','localtime', '-{HLA} hours'))
            UNION
            SELECT Placa FROM _necesitan_alertas
                WHERE TipoAlerta = 'SOAT'
                AND
                    Placa
                    NOT IN 
			        (SELECT Placa FROM InfoPlacas
		                WHERE LastUpdateApesegSoats >= datetime('now','localtime', '-{HLA2} hours'))
        """
    )
    return [i["Placa"] for i in db_cursor.fetchall()]


def get_records_revtecs(db_cursor, thresh, HLA, HLA2):
    # condition to update: will get email and no attempt to update recently
    db_cursor.execute(
        f"""SELECT Placa FROM _necesitan_mensajes_placas
                WHERE
                    Placa
                    NOT IN
                    (SELECT PlacaValidate FROM DataMtcRevisionesTecnicas
                        WHERE 
                        FechaHasta >= datetime('now','localtime', '+{thresh} days'))
                    AND
                    Placa
                    NOT IN
                    (SELECT Placa FROM InfoPlacas
                        WHERE
                        LastUpdateMtcRevisionesTecnicas >= datetime('now','localtime', '-{HLA} hours'))
            UNION
            SELECT Placa FROM _necesitan_alertas
                WHERE TipoAlerta = "REVTEC" 
				AND
                    Placa
					NOT IN
					(SELECT Placa FROM InfoPlacas
						WHERE
						LastUpdateMtcRevisionesTecnicas >= datetime('now','localtime', '-{HLA2} hours'))
        """
    )
    return [i["Placa"] for i in db_cursor.fetchall()]


def get_records_satimps(db_cursor, HLA):
    # condition to update: will get email and no attempt to update recently
    db_cursor.execute(
        f"""SELECT IdMember_FK, DocTipo, DocNum FROM _necesitan_mensajes_usuarios
                WHERE
                    IdMember_FK
                    NOT IN
			        (SELECT IdMember FROM InfoMiembros
		                WHERE LastUpdateSatImpuestosCodigos >= datetime('now','localtime', '-{HLA} hours'))
            UNION
            SELECT IdMember_FK, DocTipo, DocNum FROM _necesitan_alertas
                WHERE TipoAlerta = "SATIMP"
        """
    )
    return [(i["IdMember_FK"], i["DocTipo"], i["DocNum"]) for i in db_cursor.fetchall()]


def get_records_satmuls(db_cursor, HLA):
    # condition to update: will get email and SATMUL not updated recently
    db_cursor.execute(
        f"""SELECT Placa FROM _necesitan_mensajes_placas
                WHERE
                    Placa
                    NOT IN
                    (SELECT Placa FROM InfoPlacas
                        WHERE LastUpdateSatMultas >= datetime('now', 'localtime', '-{HLA} hours'))
        """
    )
    return [i["Placa"] for i in db_cursor.fetchall()]


def get_records_sutrans(db_cursor, HLA):
    # condition to update: will get email and SUTRAN not updated recently
    db_cursor.execute(
        f"""SELECT Placa FROM _necesitan_mensajes_placas
                WHERE
                    Placa
                    NOT IN 
			        (SELECT Placa FROM InfoPlacas
		                WHERE LastUpdateSutranMultas >= datetime('now','localtime', '-{HLA} hours'))
        """
    )
    return [i["Placa"] for i in db_cursor.fetchall()]


def get_records_recvehic(db_cursor, HLA):
    # condition to update: will get email and no attempt to update in last 48 hours
    db_cursor.execute(
        f"""SELECT IdMember_FK, DocTipo, DocNum FROM _necesitan_mensajes_usuarios
                WHERE
                    IdMember_FK
                    NOT IN
                    (SELECT IdMember FROM InfoMiembros
            		    WHERE LastUpdateMtcRecordsConductores >= datetime('now','localtime', '-{HLA} hours'))
                    AND DocTipo = 'DNI'
        """
    )
    return [(i["IdMember_FK"], i["DocTipo"], i["DocNum"]) for i in db_cursor.fetchall()]


def get_records_sunarps(db_cursor, thresh):
    # condition to update: will get email and last updated within time threshold
    db_cursor.execute(
        f""" SELECT Placa FROM _necesitan_mensajes_placas
                WHERE
                    Placa
                    NOT IN
			        (SELECT Placa FROM InfoPlacas
		                WHERE LastUpdateSunarpFichas >= datetime('now','localtime', '-{thresh} days'))
        """
    )
    return [i["Placa"] for i in db_cursor.fetchall()]


def get_records_sunats(db_cursor, HLA):
    # condition to update: will get email and no attempt to update in last 48 hours
    db_cursor.execute(
        f"""SELECT IdMember_FK, DocTipo, DocNum FROM _necesitan_mensajes_usuarios
                WHERE
                    IdMember_FK
                    NOT IN
                    (SELECT IdMember FROM InfoMiembros
            		    WHERE LastUpdateSunatRucs >= datetime('now','localtime', '-{HLA} hours'))
                    AND DocTipo = 'DNI'
        """
    )
    return [(i["IdMember_FK"], i["DocTipo"], i["DocNum"]) for i in db_cursor.fetchall()]


def get_records_jnemultas(db_cursor, HLA):
    # condition to update: will get email and no attempt to update in last 48 hours
    db_cursor.execute(
        f"""SELECT IdMember_FK, DocTipo, DocNum FROM _necesitan_mensajes_usuarios
                WHERE
                    IdMember_FK
                    NOT IN
                    (SELECT IdMember FROM InfoMiembros
            		    WHERE LastUpdateJneMultas >= datetime('now','localtime', '-{HLA} hours'))
                    AND DocTipo = 'DNI'
        """
    )
    return [(i["IdMember_FK"], i["DocNum"]) for i in db_cursor.fetchall()]


def get_records_jneafils(db_cursor, HLA):
    # condition to update: will get email and no attempt to update in last 48 hours
    db_cursor.execute(
        f"""SELECT IdMember_FK, DocTipo, DocNum FROM _necesitan_mensajes_usuarios
                WHERE
                    IdMember_FK
                    NOT IN
                    (SELECT IdMember FROM InfoMiembros
            		    WHERE LastUpdateJneAfiliaciones >= datetime('now','localtime', '-{HLA} hours'))
                    AND DocTipo = 'DNI'
        """
    )
    return [(i["IdMember_FK"], i["DocTipo"], i["DocNum"]) for i in db_cursor.fetchall()]


def get_records_osipteles(db_cursor, HLA):
    # condition to update: will get email and no attempt to update in last 48 hours
    db_cursor.execute(
        f"""SELECT IdMember_FK, DocTipo, DocNum FROM _necesitan_mensajes_usuarios
                WHERE
                    IdMember_FK
                    NOT IN
                    (SELECT IdMember FROM InfoMiembros
            		    WHERE LastUpdateOsiptelLineas >= datetime('now','localtime', '-{HLA} hours'))
                    AND DocTipo = 'DNI'
        """
    )
    return [(i["IdMember_FK"], i["DocTipo"], i["DocNum"]) for i in db_cursor.fetchall()]
