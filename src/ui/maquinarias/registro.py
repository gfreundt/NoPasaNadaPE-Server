import re
from flask import request, render_template, session


def main(self):

    # Initial page load
    if request.method == "GET":

        usuario = {
            "correo": session.get("usuario").get("correo"),
            "nombre": session.get("usuario").get("nombre"),
            "dni": "",
            "celular": "",
            "placas": "",
        }

        return render_template(
            "ui-maquinarias-registro.html",
            usuario=usuario,
            password_only=session.get("password_only"),
            third_party_login=session.get("third_party_login"),
            errors={},
        )

    # POST — form submitted
    elif request.method == "POST":

        forma = dict(request.form)

        usuario = {
            "correo": forma.get("correo"),
            "nombre": forma.get("nombre"),
            "dni": forma.get("dni"),
            "celular": forma.get("celular"),
            "placas": forma.get("placas"),
        }

        errores = validar_todo(self.db, forma)

        if errores:
            return render_template(
                "ui-maquinarias-registro.html", errors=errores, usuario=usuario
            )

        # No errors → proceed
        return render_template("ui-maquinarias-mi-cuenta.html")


# ==================================================================
# VALIDATION
# ==================================================================


def validar_todo(db, forma):

    errors = {
        "nombre": "",
        "dni": "",
        "celular": "",
        "placas": "",
        "acepta_terminos": "",
        "acepta_privacidad": "",
        "password1": "",
        "password2": "",
    }

    # --------------------------------------------------------------
    # nombre
    # --------------------------------------------------------------
    if len(forma["nombre"]) < 6:
        errors["nombre"] = "Nombre debe tener un mínimo de 6 caracteres."
    elif len(forma["nombre"]) > 50:
        errors["nombre"] = "Nombre debe tener un máximo de 50 caracteres."

    # --------------------------------------------------------------
    # dni
    # --------------------------------------------------------------
    if not re.match(r"^[0-9]{8}$", forma["dni"]):
        errors["dni"] = "DNI debe tener 8 dígitos."
    else:
        cur = db.cursor()
        cur.execute(
            "SELECT 1 FROM InfoMiembros WHERE DocNum = ? LIMIT 1", (forma["dni"],)
        )
        if cur.fetchone():
            errors["dni"] = "DNI ya está asociado a otro usuario."

    # --------------------------------------------------------------
    # celular
    # --------------------------------------------------------------
    if not re.match(r"^[0-9]{9}$", forma.get("celular", "")):
        errors["celular"] = "Celular debe tener 9 dígitos."
    else:
        cur = db.cursor()
        cur.execute(
            "SELECT 1 FROM InfoMiembros WHERE Celular = ? LIMIT 1", (forma["celular"],)
        )
        if cur.fetchone():
            errors["celular"] = "Celular ya está registrado"

    # --------------------------------------------------------------
    # placas
    # --------------------------------------------------------------
    placas_raw = forma.get("placas")
    if placas_raw:

        placas_raw = re.sub(r"\s{1,}", ",", placas_raw)
        placas_raw = placas_raw.replace(";", ",")
        placas_list = [p.strip() for p in placas_raw.split(",") if p.strip()]

        if any(len(p) != 6 for p in placas_list):
            errors["placas"] = "Todas las placas deben tener 6 caracteres."

        if len(placas_list) > 3:
            errors["placas"] = "Se pueden inscribir un máximo de 3 placas."

    # --------------------------------------------------------------
    # password
    # --------------------------------------------------------------
    password_regex = r"^(?=.*[A-Z])(?=.*[\W_])(?=.{8,}).*$"

    if not re.match(password_regex, forma.get("password1", "")):
        errors["password1"] = (
            "Contraseña debe tener mínimo 8 caracteres, "
            "incluir una mayúscula y un carácter especial."
        )

    if forma.get("password1") != forma.get("password2"):
        errors["password2"] = "Las contraseñas no coinciden."

    # --------------------------------------------------------------
    # términos y privacidad
    # --------------------------------------------------------------
    if forma.get("acepta_terminos") != "on":
        errors["acepta_terminos"] = (
            "Es necesario aceptar los términos y condiciones para continuar."
        )

    if forma.get("acepta_privacidad") != "on":
        errors["acepta_privacidad"] = (
            "Debes aceptar la política de privacidad para continuar."
        )

    # Remove empty error fields
    final_errors = {k: v for k, v in errors.items() if v}

    return final_errors
