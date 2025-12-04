import re
from datetime import datetime as dt, timedelta as td
from flask import redirect, request, render_template, url_for, session

from src.utils.utils import compare_text_to_hash, date_to_mail_format
from src.ui.maquinarias import data_servicios, servicios


# login endpoint
def main(self):

    cursor = self.db.cursor()
    conn = self.db.conn
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
    forma = dict(request.form)

    # FIRST STEP: validating email only
    if request.form["show_password_field"] == "false":

        # Validate email format
        error_formato = validar_formato(forma["correo_ingresado"])
        if error_formato:
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=False,
                errors=error_formato,
                user_data=forma,
            )

        # Validate email is authorized
        error_autorizacion = validar_autorizacion(cursor, forma["correo_ingresado"])
        if error_autorizacion:
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=False,
                errors=error_autorizacion,
                user_data=forma,
            )

        # Validate subscription
        suscrito = validar_suscripcion(cursor, forma["correo_ingresado"])
        if not suscrito:
            session["usuario"] = {"correo": forma["correo_ingresado"]}
            session["password_only"] = False
            session["third_party_login"] = False

            return redirect("/maquinarias/registro")

        # Check if account is blocked
        cuenta_bloqueada = validar_bloqueo_cuenta(cursor, forma["correo_ingresado"])
        if cuenta_bloqueada:
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=False,
                errors=cuenta_bloqueada,
                user_data=forma,
            )

        # All good → show password field
        return render_template(
            "ui-maquinarias-login.html",
            show_password_field=True,
            errors={},
            user_data=forma,
        )

    # SECOND STEP: validating password
    elif forma["show_password_field"] == "true":

        error_acceso, mostrar_campo_password = validar_password(
            cursor,
            conn,
            forma["correo_ingresado"],
            forma["password_ingresado"],
        )

        if error_acceso:
            # Remove bad password
            forma.update({"password_ingresado": ""})
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=mostrar_campo_password,
                errors=error_acceso,
                user_data=forma,
            )

        # Correct password → reset attempts
        resetear_logins_fallidos(cursor, conn, correo=forma["correo_ingresado"])

        # extraer informacion de base de datos (usuario y mi-cuenta)
        extraer_data_usuario(cursor, correo=forma["correo_ingresado"])

        return servicios.main(cursor, correo=forma["correo_ingresado"])


def extraer_data_usuario(cursor, correo):

    # datos de usuario
    cursor.execute(
        "SELECT IdMember, NombreCompleto, DocTipo, DocNum, Celular, Password FROM InfoMiembros WHERE Correo = ? LIMIT 1",
        (correo,),
    )
    a = cursor.fetchone()

    # datos de placas
    cursor.execute(
        "SELECT Placa FROM InfoPlacas WHERE IdMember_FK = ?",
        (a["IdMember"],),
    )
    placas = ", ".join(i["Placa"] for i in cursor.fetchall())

    session["usuario"] = {
        "id_member": a["IdMember"],
        "correo": correo,
        "nombre": a["NombreCompleto"],
        "tipo_documento": a["DocTipo"],
        "numero_documento": a["DocNum"],
        "celular": a["Celular"],
        "placas": placas,
        "password": a["Password"],
    }


# =====================================================================
# VALIDATION FUNCTIONS
# =====================================================================


def validar_formato(correo):
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", correo):
        return {"correo": "Formato de correo inválido."}
    return {}


def validar_autorizacion(cursor, correo):
    cmd = "SELECT Correo FROM InfoClientesAutorizados WHERE Correo = ?"
    cursor.execute(cmd, (correo,))
    if not cursor.fetchone():
        return {"correo": "Correo no autorizado para este servicio."}
    return {}


def validar_suscripcion(cursor, correo):
    cmd = "SELECT Correo FROM InfoMiembros WHERE Correo = ?"
    cursor.execute(cmd, (correo,))
    return bool(cursor.fetchone())


def validar_bloqueo_cuenta(cursor, correo):
    cmd = "SELECT NextLoginAllowed FROM InfoMiembros WHERE Correo = ?"
    cursor.execute(cmd, (correo,))
    row = cursor.fetchone()

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


def validar_password(cursor, conn, correo, password):
    # Get hashed password
    cmd = "SELECT Password FROM InfoMiembros WHERE Correo = ?"
    cursor.execute(cmd, (correo,))
    row = cursor.fetchone()

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

        cursor.execute(cmd, (correo,))
        logins_fallidos = cursor.fetchone()[0]

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
            cursor.execute(
                cmd, (dt.strftime(bloqueo_hasta, "%Y-%m-%d %H:%M:%S"), correo)
            )

        conn.commit()

        return error, mostrar_campo_password

    # Correct password
    return {}, ""


def resetear_logins_fallidos(cursor, conn, correo):
    cmd = "UPDATE InfoMiembros SET NextLoginAllowed = NULL, CountFailedLogins = 0 WHERE Correo = ?"
    cursor.execute(cmd, (correo,))
    conn.commit()
