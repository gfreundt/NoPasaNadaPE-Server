import re
from datetime import datetime as dt, timedelta as td
from flask import redirect, request, render_template, url_for, session

from src.utils.utils import compare_text_to_hash


# login endpoint
def main(self):

    self.session.permanent = True

    if request.method == "HEAD":
        return ("", 200)

    if self.session.get("loaded_user"):
        return redirect(url_for("maq-status"))

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
        resetear_logins_fallidos(self.db, form["correo_ingresado"])
        return render_template("ui-maquinarias-mi-cuenta.html")


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
            bloqueo_hasta = dt.now() + td(days=1)
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
