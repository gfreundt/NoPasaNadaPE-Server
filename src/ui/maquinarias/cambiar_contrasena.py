import re
from datetime import datetime as dt
from flask import request, render_template, session, redirect, url_for

from src.utils.constants import FORMATO_PASSWORD
from src.utils.utils import hash_text
from src.comms import enviar_correo_inmediato


def main(self, token):

    # respuesta a pings para medir uptime
    if request.method == "HEAD":
        return ("", 200)

    # Initial page load
    if request.method == "GET" or not session["usuario"].get("correo"):

        # navegada directa a la pagina sin token asociado
        if not token:
            return redirect("maquinarias")

        cursor = self.db.cursor()
        cmd = "SELECT Correo, FechaHasta, TokenUsado FROM StatusTokens WHERE TokenHash = ? AND TokenTipo = ? LIMIT 1"
        cursor.execute(cmd, (token, "Password"))
        resultado = cursor.fetchone()

        # navegada directa a la pagina con un token que no ha sido generado por el sistema
        if not resultado:
            invalido = "Token Invalido"

        else:
            session["usuario"] = {"correo": resultado["Correo"]}

            if resultado["TokenUsado"]:
                invalido = "Token Usado."
            elif (
                dt.strptime(resultado["FechaHasta"], "%Y-%m-%d %H:%M:%S.%f") < dt.now()
            ):
                invalido = "Token Vencido."
            else:
                invalido = ""

        return render_template(
            "ui-maquinarias-nueva-contrasena.html",
            invalido=invalido,
            usuario=session["usuario"],
            errors=[],
        )

    # POST — form submitted
    elif request.method == "POST":

        errors = []
        forma = dict(request.form)
        errores = validaciones(forma)

        if errores:
            return render_template(
                "ui-maquinarias-nueva-contrasena.html",
                invalido=[],
                usuario=session["usuario"]["correo"],
                errors=errors,
            )

        # No errors → proceed
        cursor = self.db.cursor()
        conn = self.db.conn
        if forma.get("password1"):
            # grabar cambios
            cmd = "UPDATE InfoMiembros SET Password = ? WHERE Correo = ?"
            cursor.execute(
                cmd, (hash_text(forma.get("password1")), session["usuario"]["correo"])
            )
            # desautorizar token
            cmd = "UPDATE StatusTokens SET TokenUsado = 1 WHERE Correo = ?"
            cursor.execute(cmd, (session["usuario"]["correo"],))

            conn.commit()
            # correo de confirmarcion de cambio de contrasena
            enviar_correo_inmediato.confirmacion_cambio_contrasena(
                self.db, correo=session["usuario"]["correo"]
            )

        session.clear()
        return redirect(url_for("maquinarias"))


# ==================================================================
# VALIDATION
# ==================================================================


def validaciones(forma):

    errors = {
        "password1": "",
        "password2": "",
    }

    # --------------------------------------------------------------
    # password
    # --------------------------------------------------------------
    if not re.match(FORMATO_PASSWORD["regex"], forma.get("password1", "")):
        errors["password1"] = FORMATO_PASSWORD["mensaje"]

    elif forma.get("password1") != forma.get("password2"):
        errors["password2"] = "Las contraseñas no coinciden."

    # Remove empty error fields
    return {k: v for k, v in errors.items() if v}
