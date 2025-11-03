import re
from datetime import datetime as dt, timedelta as td
from flask import render_template, redirect, request, flash

from src.comms import send_instant_email
from src.utils.utils import hash_text,compare_text_to_hash


def main(self):

    # primera carga de pagina
    if request.method == "GET":

        # load user data into session variable
        self.load_user_data_into_session(self.session["login_correo"])

        # get next message date and calculate days until
        self.sgte_boletin = {}
        if self.session["loaded_user"]["NextMessageSend"]:
            self.sgte_boletin["fecha"] = self.session["loaded_user"]["NextMessageSend"][
                :10
            ]
            self.sgte_boletin["dias"] = (
                dt.strptime(
                    self.session["loaded_user"]["NextMessageSend"], "%Y-%m-%d %H:%M:%S"
                )
                - dt.now()
            ).days + 1
        else:
            self.sgte_boletin["fecha"] = (dt.now() + td(days=1)).strftime("%Y-%m-%d")
            self.sgte_boletin["dias"] = 1

        _user = {
            "codigo": self.session["loaded_user"]["CodMember"],
            "correo": self.session["loaded_user"]["Correo"],
            "dni": self.session["loaded_user"]["DocNum"],
            "nombre": self.session["loaded_user"]["NombreCompleto"],
            "celular": self.session["loaded_user"]["Celular"],
        }

        return render_template(
            "cuenta-mis-datos.html",
            user=_user,
            placas=self.loaded_placas,
            sgte_boletin=self.sgte_boletin,
            errors={},
        )

    # procesar cambios
    if request.method == "POST":
        form_response = dict(request.form)

        # remove account - copy member to another table, erase from main one and unattach placa
        if "eliminar" in form_response:

            cmd = f""" INSERT INTO InfoMiembrosInactivos SELECT * FROM InfoMiembros WHERE IdMember = {self.session["loaded_user"]['IdMember']};
                       DELETE FROM InfoMiembros WHERE IdMember = {self.session["loaded_user"]['IdMember']};
                       UPDATE InfoPlacas SET IdMember_FK = 0 WHERE IdMember_FK = {self.session["loaded_user"]['IdMember']}
                    """
            self.db.cursor.executescript(cmd)

            # send email to cancelled user
            send_instant_email.send_cancel(
                correo=self.session["loaded_user"]["Correo"],
                nombre=self.session["loaded_user"]["NombreCompleto"],
            )

            self.log(
                message=f"Eliminado {self.session['loaded_user']['CodMember']} | {self.session['loaded_user']['NombreCompleto']} | {self.session['loaded_user']['DocNum']} | {self.session['loaded_user']['Correo']}"
            )
            flash("Usuario eliminado.", "success")
            return redirect("logout")

        # check for changes made to user information
        changes_made = validation_changes(
            user=self.session["loaded_user"],
            placas=self.loaded_placas,
            post=form_response,
        )

        # no changes made
        if changes_made:

            errors = validation(form_response, db=self.db)

            # hay errores
            if any(errors.values()):

                _user = {
                    "codigo": self.session["loaded_user"]["CodMember"],
                    "correo": self.session["loaded_user"]["Correo"],
                    "dni": self.session["loaded_user"]["DocNum"],
                    "nombre": form_response["nombre"],
                    "celular": form_response["celular"],
                }
                _placas = {
                    "placa1": form_response["placa1"],
                    "placa2": form_response["placa2"],
                    "placa3": form_response["placa3"],
                }

                return render_template(
                    "cuenta-mis-datos.html",
                    user=_user,
                    placas=_placas,
                    sgte_boletin=self.sgte_boletin,
                    errors=errors,
                )

            # sin errores
            else:
                # if user made changes to placas, update next message to be sent in 2 hours, else leave blank
                _update_next_message_send = (
                    f", NextMessageSend = '{(dt.now() + td(hours=2)).strftime("%Y-%m-%d %H:%M:%S")}' "
                    if "Placas" in changes_made
                    else ""
                )
                self.db.cursor.execute(
                    f"""    UPDATE InfoMiembros SET
                            NombreCompleto = '{form_response["nombre"]}',
                            DocNum = '{form_response["dni"]}',
                            Celular = '{form_response["celular"]}'
                            {_update_next_message_send}
                            WHERE IdMember = {self.session["loaded_user"]['IdMember']}"""
                )

                # update contraseña if changed
                if "Contraseña" in changes_made:
                    self.db.cursor.execute(
                        f"""    UPDATE InfoMiembros SET Password = '{hash_text(form_response["contra2"])}'
                                WHERE IdMember = {self.session["loaded_user"]['IdMember']}
                        """
                    )

                # erase foreign key linking placa to member
                self.db.cursor.execute(
                    f"UPDATE InfoPlacas SET IdMember_FK = 0 WHERE IdMember_FK = {self.session["loaded_user"]['IdMember']}"
                )

                # loop all non-empty placas and link foreign key to member if placa exists or create new placa record
                for placa in [
                    i
                    for i in (
                        form_response["placa1"],
                        form_response["placa2"],
                        form_response["placa3"],
                    )
                    if i
                ]:

                    self.db.cursor.execute(
                        f"SELECT * FROM InfoPlacas WHERE Placa = '{placa.upper()}'"
                    )
                    if len(self.db.cursor.fetchall()) > 0:
                        # placa already exists in the database, assign foreign key to member
                        self.db.cursor.execute(
                            f"UPDATE InfoPlacas SET IdMember_FK = {self.session["loaded_user"]['IdMember']} WHERE Placa = '{placa}'"
                        )
                    else:
                        # create new record
                        self.db.cursor.execute(
                            "SELECT IdPlaca FROM InfoPlacas ORDER BY IdPlaca DESC"
                        )
                        rec = int(self.db.cursor.fetchone()["IdPlaca"]) + 1
                        _ph = "2020-01-01"  # default placeholder value for date of last scrape for new placas
                        self.db.cursor.execute(
                            f"INSERT INTO InfoPlacas VALUES ({rec}, {self.session["loaded_user"]['IdMember']}, '{placa}', '{_ph}', '{_ph}', '{_ph}', '{_ph}', '{_ph}')"
                        )

                self.db.conn.commit()
                flash(changes_made, "success")
                self.log(
                    message=f"Actualizado {self.session["loaded_user"]['CodMember']} | {self.session["loaded_user"]['NombreCompleto']} | {self.session["loaded_user"]['DocNum']} | {self.session["loaded_user"]['Correo']}"
                )

        else:
            flash("No se realizaron cambios. ", "warning")

        return redirect("mis-datos")


def validation(form_response, db):

    # realizar todas las validaciones
    errors = {
        "placa1": [],
        "placa2": [],
        "placa3": [],
        "dni": [],
        "nombre": [],
        "celular": [],
        "contra1": [],
        "contra2": [],
        "contra3": [],
    }

    # nombre
    if len(form_response["nombre"]) < 5:
        errors["nombre"].append("Nombre debe tener mínimo 5 letras")

    # celular: formato correcto (9 digitos)
    if not re.match(r"^[0-9]{9}$", form_response["celular"]):
        errors["celular"].append("Ingrese un celular válido")

    # celular: no se esta duplicando con otro celular de la base de datos (no necesario revisar si hay error previo)
    else:
        db.cursor.execute(
            f"SELECT Celular FROM InfoMiembros WHERE Celular = '{form_response["celular"]}' AND IdMember != (select IdMember FROM InfoMiembros WHERE DocNum='{form_response["dni"]}')"
        )
        if db.cursor.fetchone():
            errors["celular"].append("Celular ya está asociado con otra cuenta.")

    # placas
    for p in range(1, 4):

        _index = f"placa{p}"

        # debe ser exactamente 6 letras y/o numeros, minimo 1 numero en todo el texto
        if form_response[_index] and not re.match(
            r"^(?=.*\d)[A-Z0-9]{6}$", form_response[_index]
        ):
            errors[_index].append("Usar un formato válido")

        # no se esta duplicando con otra placa de la base de datos (no necesario revisar si hay error previo)
        else:
            db.cursor.execute(
                f"SELECT Placa FROM InfoPlacas WHERE Placa = '{form_response[_index]}' AND IdMember_FK != 0 AND IdMember_FK != (select IdMember FROM InfoMiembros WHERE DocNum='{form_response["dni"]}')"
            )
            if db.cursor.fetchone():
                errors[_index].append("Placa ya está asociada con otra cuenta.")

    # revisar solo si se ingreso algo en el campo de contraseña actual
    if len(form_response["contra1"]) > 0:

        # contraseña actual
        db.cursor.execute(
            f"SELECT Password FROM InfoMiembros WHERE Correo = '{form_response["correo"]}'"
        )
        _password = db.cursor.fetchone()[0]

        if not compare_text_to_hash(form_response["contra1"], _password): #password != str(form_response["contra1"]):
            errors["contra1"].append("Contraseña equivocada")

        # contraseña nueva
        elif not re.match(r"^(?=.*[A-Z])(?=.*\d).{6,20}$", form_response["contra2"]):
            errors["contra2"].append("Mínimo 6 caracteres, incluir mayúscula y número")

        # validacion de nueva contraseña
        elif form_response["contra2"] != form_response["contra3"]:
            errors["contra3"].append("Contraseñas no coinciden")

    return errors


def validation_changes(user, placas, post):

    changes = ""

    # nombre ha cambiado
    if user["NombreCompleto"] != post["nombre"]:
        changes += "Nombre actualizado. "

    # celular ha cambiado
    if user["Celular"] != post["celular"]:
        changes += "Celular actualizado. "

    # alguna placa ha cambiado
    if sorted(
        [i for i in (post["placa1"], post["placa2"], post["placa3"]) if i]
    ) != sorted(placas):
        changes += "Placas actualizadas. "

    # contraseña ha cambiado
    if len(post["contra1"]) > 0 and str(post["contra2"]) != user["Password"]:
        changes += "Contraseña actualizada. "

    return changes

