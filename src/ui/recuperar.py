import re
from random import randrange
from string import ascii_uppercase
from flask import render_template, request, flash

from src.comms import send_instant_email


def main(self):

    # empty data for first time
    if request.method == "GET":
        self.page = 1
        return render_template("ui-recuperar-1.html", user={}, errors={})

    # recibir datos de formulario de recuperacion y validar - pagina 1/2
    if request.method == "POST" and self.page == 1:
        form_response = dict(request.form)
        errors = validation(db=self.db, attempt=form_response, page=1)

        # no errors
        if not any(errors.values()):
            # keep data for second part of recovery
            self.session["recovery_attempt"] = form_response

            # generate validation code
            self.session["codigo_generado"] = "".join(
                [ascii_uppercase[randrange(0, len(ascii_uppercase))] for _ in range(4)]
            )
            print("-------- REC ---------->", self.session["codigo_generado"])
            self.db.cursor.execute(
                "SELECT NombreCompleto FROM InfoMiembros WHERE Correo = ?",
                (self.session["recovery_attempt"]["correo"],),
            )
            send_instant_email.send_code(
                codigo=self.session["codigo_generado"],
                correo=self.session["recovery_attempt"]["correo"],
                nombre=self.db.cursor.fetchone()["NombreCompleto"],
            )

            self.log(
                message=f"Recuperacion. Correo enviado. {str(form_response["correo"])}."
            )
            self.page = 2
            return render_template(
                "ui-recuperar-2.html", user=form_response, errors=errors
            )

        # errors in submitted form
        else:

            return render_template(
                "ui-recuperar-1.html", user=form_response, errors=errors
            )

    # recibir datos de formulario de recuperacion y validar - pagina 2/2
    if request.method == "POST" and self.page == 2:
        form_response = dict(request.form)
        errors = validation(
            self.db,
            attempt=form_response,
            codigo=self.session["codigo_generado"],
            page=2,
        )

        # no errors
        if not any(errors.values()):

            # define all values to be included in database
            self.db.cursor.execute(
                "UPDATE InfoMiembros SET Password = ? WHERE Correo = ?",
                (request.form["password1"], self.session["recovery_attempt"]["correo"]),
            )
            self.db.conn.commit()
            self.log(
                message=f"Recuperacion ok. {self.session["recovery_attempt"]["correo"]}"
            )

            # clear self.session data (back to login) and reload db to include new record
            self.session.clear()
            flash("Contraseña cambiada correctamente.", "success")
            return render_template("ui-login.html", user={}, errors={})
        else:
            form_response["password1"] = ""
            form_response["password2"] = ""
            return render_template(
                "ui-recuperar-2.html", user=form_response, errors=errors
            )

    # catch errors and return to login page
    self.session.clear()
    return render_template("ui-login.html", user={}, errors={})


def validation(db, attempt, page, codigo=None):

    # self.load_members()

    # realizar todas las validaciones
    errors = {
        "correo": [],
        "codigo": [],
        "password1": [],
        "password2": [],
    }

    if page == 1:

        # correo
        if not re.match(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", attempt["correo"]
        ):
            errors["correo"].append("Ingresa un correo válido")
        else:
            db.cursor.execute(
                "SELECT * FROM InfoMiembros WHERE Correo = ? LIMIT 1",
                (attempt["correo"],),
            )
            if not db.cursor.fetchone():
                errors["correo"].append("Correo no registrado.")

    elif page == 2:

        # codigo
        if not re.match(r"^[A-Za-z]{4}$", attempt["codigo"]):
            errors["codigo"].append("Código de validación son 4 letras")
        if attempt["codigo"].upper() != codigo:
            errors["codigo"].append("Código de validación incorrecto")

        # contraseña
        if not re.match(r"^(?=.*[A-Z])(?=.*\d).{6,20}$", attempt["password1"]):
            errors["password1"].append(
                "Al menos 6 caracteres e incluir una mayúscula y un número"
            )

        # validacion de contraseña
        if attempt["password1"] != attempt["password2"]:
            errors["password2"].append("Contraseñas no coinciden")

    return errors
