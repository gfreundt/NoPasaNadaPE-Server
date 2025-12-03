import re
from datetime import datetime as dt, timedelta as td
from flask import redirect, request, render_template, url_for, session

from src.utils.utils import compare_text_to_hash, date_to_mail_format
from src.utils.constants import SQL_TABLES


# login endpoint
def main(self):

    self.session.permanent = True

    if request.method == "HEAD":
        return ("", 200)

    # if self.session.get("loaded_user"):
    #     return redirect(url_for("maquinarias-mi-cuenta"))

    # GET -> load initial page
    if request.method == "GET":
        return render_template(
            "ui-maquinarias-login.html",
            show_password_field=False,
            errors={},
            user_data={},
        )

    # POST -> form submitted
    form = dict(request.form)

    # FIRST STEP: validating email only
    if request.form["show_password_field"] == "false":

        # Validate email format
        error_formato = validar_formato(form["correo_ingresado"])
        if error_formato:
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=False,
                errors=error_formato,
                user_data=form,
            )

        # Validate email is authorized
        error_autorizacion = validar_autorizacion(self.db, form["correo_ingresado"])
        if error_autorizacion:
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=False,
                errors=error_autorizacion,
                user_data=form,
            )

        # Validate subscription
        suscrito = validar_suscripcion(self.db, form["correo_ingresado"])
        if not suscrito:
            session["usuario"] = {"correo": form["correo_ingresado"]}
            session["password_only"] = False
            session["third_party_login"] = False

            return redirect("/maquinarias/registro")

        # Check if account is blocked
        cuenta_bloqueada = validar_bloqueo_cuenta(self.db, form["correo_ingresado"])
        if cuenta_bloqueada:
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=False,
                errors=cuenta_bloqueada,
                user_data=form,
            )

        # All good → show password field
        return render_template(
            "ui-maquinarias-login.html",
            show_password_field=True,
            errors={},
            user_data=form,
        )

    # SECOND STEP: validating password
    elif form["show_password_field"] == "true":

        error_acceso, mostrar_campo_password = validar_password(
            self.db,
            form["correo_ingresado"],
            form["password_ingresado"],
        )

        if error_acceso:
            # Remove bad password
            form.update({"password_ingresado": ""})
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=mostrar_campo_password,
                errors=error_acceso,
                user_data=form,
            )

        # Correct password → reset attempts
        resetear_logins_fallidos(self.db, correo=form["correo_ingresado"])
        servicios, documentos = generar_data_servicios(
            self.db, correo=form["correo_ingresado"]
        )
        return render_template(
            "ui-maquinarias-mi-cuenta.html", servicios=servicios, documentos=documentos
        )


# =====================================================================
# VALIDATION FUNCTIONS
# =====================================================================


def validar_formato(correo):
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", correo):
        return {"correo": "Formato de correo inválido."}
    return {}


def validar_autorizacion(db, correo):
    cmd = "SELECT Correo FROM InfoClientesAutorizados WHERE Correo = ?"
    cur = db.cursor()
    cur.execute(cmd, (correo,))
    if not cur.fetchone():
        return {"correo": "Correo no autorizado para este servicio."}
    return {}


def validar_suscripcion(db, correo):
    cmd = "SELECT Correo FROM InfoMiembros WHERE Correo = ?"
    cur = db.cursor()
    cur.execute(cmd, (correo,))
    return bool(cur.fetchone())


def validar_bloqueo_cuenta(db, correo):
    cmd = "SELECT NextLoginAllowed FROM InfoMiembros WHERE Correo = ?"
    cur = db.cursor()
    cur.execute(cmd, (correo,))
    row = cur.fetchone()

    if not row:
        return None

    bloqueo_liberado = row[0]

    if (
        bloqueo_liberado
        and dt.strptime(bloqueo_liberado, "%Y-%m-%d %H:%M:%S") > dt.now()
    ):
        return {
            "correo": "Tu cuenta esta temporalmente bloqueada: muchos intentos equivocados."
        }

    return None


def validar_password(db, correo, password):
    # Get hashed password
    cmd = "SELECT Password FROM InfoMiembros WHERE Correo = ?"
    cur = db.cursor()
    cur.execute(cmd, (correo,))
    row = cur.fetchone()

    if not row:
        return {"correo": "Cuenta no encontrada."}, True

    stored_hash = row[0]

    # Compare hashes
    if not compare_text_to_hash(text_string=password, hash_string=stored_hash):

        # Increase failed login count
        cmd = """UPDATE InfoMiembros 
                 SET CountFailedLogins = CountFailedLogins + 1 
                 WHERE Correo = ?
                 RETURNING CountFailedLogins;"""

        cur = db.cursor()
        cur.execute(cmd, (correo,))
        logins_fallidos = cur.fetchone()[0]

        error = {"password": "Contraseña equivocada"}
        bloqueo_hasta = None
        mostrar_campo_password = True

        if logins_fallidos == 3:
            bloqueo_hasta = dt.now() + td(minutes=15)
            error = {"correo": "Cuenta bloqueada por 15 minutos."}
            mostrar_campo_password = False

        elif logins_fallidos == 4:
            bloqueo_hasta = dt.now() + td(minutes=60)
            error = {"correo": "Cuenta bloqueada por 1 hora."}
            mostrar_campo_password = False

        elif logins_fallidos >= 5:
            bloqueo_hasta = dt.now() + td(Dias=1)
            error = {"correo": "Cuenta bloqueada por 1 día."}
            mostrar_campo_password = False

        # Update lock expiration if needed
        if bloqueo_hasta:
            cmd = "UPDATE InfoMiembros SET NextLoginAllowed = ? WHERE Correo = ?"
            cur = db.cursor()
            cur.execute(cmd, (dt.strftime(bloqueo_hasta, "%Y-%m-%d %H:%M:%S"), correo))

        db.commit()

        return error, mostrar_campo_password

    # Correct password
    return {}, ""


def resetear_logins_fallidos(db, correo):
    cmd = "UPDATE InfoMiembros SET NextLoginAllowed = NULL, CountFailedLogins = 0 WHERE Correo = ?"
    cur = db.cursor()
    cur.execute(cmd, (correo,))
    db.commit()


def generar_data_servicios(db, correo):

    cursor = db.cursor()

    _txtal = []
    _attachments = []
    _attach_txt = []
    _info = {}

    # obtener informacion de miembro y placa, almacenar en variables
    cursor.execute(
        "SELECT IdMember, LastUpdateMtcBrevetes, LastUpdateMtcRecordsConductores, LastUpdateSatImpuestosCodigos FROM InfoMiembros WHERE Correo = ? LIMIT 1",
        (correo,),
    )
    data_miembro = cursor.fetchone()
    id_member = data_miembro["IdMember"]

    cursor.execute(
        "SELECT * FROM InfoPlacas WHERE IdMember_FK = ?",
        (data_miembro["IdMember"],),
    )
    data_placas = cursor.fetchall()
    placas = [i["Placa"] for i in data_placas]

    desconocido = {
        "Estado": "Desconocido",
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
    i = dict(cursor.fetchone())
    vencimientos.update({"brevete": i if i else desconocido})

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
    vencimientos.update({"soats": [dict(i) for i in cursor.fetchall()]})

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
    vencimientos.update({"revtecs": [dict(i) for i in cursor.fetchall()]})

    # impuestos SAT
    cmd = f"""  SELECT
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
    vencimientos.update({"satimps": [dict(i) for i in cursor.fetchall()]})

    # multas SAT
    cmd = f"""  SELECT
                Falta, FechaEmision, Deuda, Estado, LastUpdate
                FROM
                DataSatMultas
                WHERE
                PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {id_member})
            """
    cursor.execute(cmd)
    multas.update({"satmuls": [dict(i) for i in cursor.fetchall()]})

    # multas SUTRAN
    cmd = f"""  SELECT
                CodigoInfrac, FechaDoc, Clasificacion, LastUpdate
                FROM
                DataSutranMultas
                WHERE
                PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {id_member})
            """
    cursor.execute(cmd)
    multas.update({"sutrans": [dict(i) for i in cursor.fetchall()]})

    from pprint import pprint

    pprint(vencimientos)
    pprint(multas)
