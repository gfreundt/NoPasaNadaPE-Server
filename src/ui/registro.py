import re
from datetime import datetime as dt
import uuid
from random import randrange
from string import ascii_uppercase
from flask import render_template, request, flash, redirect

from src.comms import send_instant_email
from src.utils.utils import hash_text


# fix
def main(self):

    # cargando la data inicial de la pagina 1
    if request.method == "GET":
        self.page = 1
        return render_template("ui-registro-1.html", user={}, errors={})

    # recibir datos de registro y validar - pagina 1/2
    elif request.method == "POST" and self.page == 1:
        form_response = dict(request.form)
        print(form_response)
        errors = validation(db=self.db, attempt=form_response, page=1)

        # no errors
        if not any(errors.values()):
            # keep data for second part of registration
            self.session["registration_attempt"] = form_response

            # generate validation code
            self.session["codigo_generado"] = "".join(
                [ascii_uppercase[randrange(0, len(ascii_uppercase))] for _ in range(4)]
            )
            print("-------- REG ---------->", self.session["codigo_generado"])
            send_instant_email.send_code(
                codigo=self.session["codigo_generado"],
                correo=self.session["registration_attempt"]["correo"],
                nombre=self.session["registration_attempt"]["nombre"],
            )
            self.log(
                message=f"Nuevo Registro. Correo enviado. {form_response['correo']}."
            )
            self.page = 2
            return render_template(
                "ui-registro-2.html", user=form_response, errors=errors
            )

        # errors in submitted form
        else:
            return render_template(
                "ui-registro-1.html", user=form_response, errors=errors
            )

    # recibir datos de registro y validar - pagina 2/2
    elif request.method == "POST" and self.page == 2:
        form_response = dict(request.form)
        errors = validation(
            db=self.db,
            attempt=form_response,
            codigo=self.session["codigo_generado"],
            page=2,
        )

        # no errors
        if not any(errors.values()):

            # get next record id
            self.db.cursor.execute("SELECT MAX(IdMember) FROM InfoMiembros")
            new_id = self.db.cursor.fetchone()[0] + 1

            # write new record in members table and create record in last update table
            default_date = "2020-01-01"
            registration = self.session["registration_attempt"]

            _nr = {
                "IdMember": new_id,
                "CodMember": "NPN-" + str(uuid.uuid4())[-6:].upper(),
                "NombreCompleto": registration["nombre"],
                "DocTipo": "DNI",
                "DocNum": registration["dni"],
                "Celular": registration["celular"],
                "Correo": registration["correo"],
                "LastUpdateMtcBrevetes": default_date,
                "LastUpdateMtcRecordsConductores": default_date,
                "LastUpdateSatImpuestosCodigos": default_date,
                "LastUpdateSunatRucs": default_date,
                "LastUpdateJneMultas": default_date,
                "LastUpdateOsiptelLineas": default_date,
                "LastUpdateJneAfiliaciones": default_date,
                "LastLoginDatetime": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                "CountFailedLogins": 0,
                "Password": hash_text(request.form["password1"]),
                "ForceMsg": 0,
                "NextMessageSend": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            self.db.cursor.execute(
                f"INSERT INTO InfoMiembros {tuple(_nr.keys())} VALUES {tuple(_nr.values())}"
            )
            self.db.conn.commit()
            self.log(message=f"Nuevo Registro Completo: {str(_nr)}")

            # send welcome email to successfully registered new user
            send_instant_email.send_welcome(
                correo=self.session["registration_attempt"]["correo"],
                nombre=self.session["registration_attempt"]["nombre"],
            )

            # clear session data and reload db to include new record
            self.session.clear()

            # log in recently created user and success message
            self.session["login_correo"] = registration["correo"]
            self.page = 0  # reset
            flash("Usario creado con éxito", "success")
            return redirect("mis-datos")

        # errors in submitted form
        else:
            form_response["password1"] = ""
            form_response["password2"] = ""
            return render_template(
                "ui-registro-2.html", user=form_response, errors=errors
            )


def validation(db, attempt, page, codigo=None):
    # realizar todas las validaciones
    errors = {
        "nombre": [],
        "dni": [],
        "correo": [],
        "celular": [],
        "acepta_terminos": [],
        "acepta_privacidad": [],
        "codigo": [],
        "password1": [],
        "password2": [],
    }

    if page == 1:

        # nombre
        if len(attempt["nombre"]) < 5:
            errors["nombre"].append("Nombre debe tener mínimo 5 letras")

        # dni
        if not re.match(r"^[0-9]{8}$", attempt["dni"]):
            errors["dni"].append("DNI solamente debe tener 8 dígitos")
        else:
            db.cursor.execute(
                "SELECT * FROM InfoMiembros WHERE DocNum = ? LIMIT 1", (attempt["dni"],)
            )
            if db.cursor.fetchone():
                errors["dni"].append("DNI ya está registado")

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
            if db.cursor.fetchone():
                errors["correo"].append("Correo ya está registado")

        # celular
        if not re.match(r"^[0-9]{9}$", attempt["celular"]):
            errors["celular"].append("Ingresa un celular válido")
        else:
            db.cursor.execute(
                "SELECT * FROM InfoMiembros WHERE Celular = ? LIMIT 1",
                (attempt["celular"],),
            )
            if db.cursor.fetchone():
                errors["celular"].append("Celular ya está registado")

        # acepta terminos y condiciones / politica de privacidad
        if not attempt.get("acepta_terminos"):
            errors["acepta_terminos"].append(
                "Debes aceptar los términos y condiciones para continuar"
            )
        if not attempt.get("acepta_privacidad"):
            errors["acepta_privacidad"].append(
                "Debes aceptar la política de privacidad para continuar"
            )

    elif page == 2:

        # codigo
        if not re.match(r"^[A-Za-z]{4}$", attempt["codigo"]):
            errors["codigo"].append("Codigo de validacion son 4 letras")
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
