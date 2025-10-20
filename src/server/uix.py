from datetime import datetime as dt
from datetime import timedelta as td
from flask import redirect, render_template, request, flash

from src.comms import send_instant_email


# mi cuenta endpoint (NAVBAR)
def mis_datos_1(self):

    # user not logged in, got to login page
    if "user" not in self.session:
        return redirect("login")

    # extract user data
    self.db.cursor.execute(
        f"SELECT * FROM InfoMiembros WHERE IdMember = {self.session['user']['IdMember']}"
    )
    user = self.db.cursor.fetchone()
    self.db.cursor.execute(
        f"SELECT * FROM InfoPlacas WHERE IdMember_FK = {self.session['user']['IdMember']}"
    )
    placas = [i["Placa"] for i in self.db.cursor.fetchall()]

    # get next message date
    self.db.cursor.execute(
        f"SELECT FechaEnvio FROM StatusMensajesEnviados WHERE IdMember_FK = {self.session['user']['IdMember']} ORDER BY FechaEnvio DESC"
    )
    _fecha = self.db.cursor.fetchone()
    if not _fecha:
        _siguiente_mensaje = (dt.now() + td(days=1)).strftime("%Y-%m-%d")
        _dias_faltantes = 1
    else:
        _siguiente_mensaje = max(
            dt.strptime(_fecha[0], "%Y-%m-%d %H:%M:%S") + td(days=30),
            dt.now() + td(days=1),
        ).strftime("%Y-%m-%d")
        _dias_faltantes = (
            dt.strptime(_fecha[0], "%Y-%m-%d %H:%M:%S") - dt.now() + td(days=30)
        ).days

    sgte_boletin = {"fecha": _siguiente_mensaje, "dias": _dias_faltantes}

    # empty data for first time
    errors = {}

    if request.method == "GET":
        pass

    # validating form response
    elif request.method == "POST":
        form_response = dict(request.form)

        # check if there were changes to account
        errors = self.validacion.mic(form_response)
        changes_made = self.validacion.mic_changes(
            user=user, placas=placas, post=form_response
        )

        # update template data
        user = (
            self.session["user"]["IdMember"],
            form_response["codigo"],
            form_response["nombre"],
            self.session["user"]["DocTipo"],
            form_response["dni"],
            form_response["celular"],
            form_response["correo"],
        )
        placas = (
            form_response["placa1"],
            form_response["placa2"],
            form_response["placa3"],
        )

        # remove account - copy member to another table, erase from main one and unattach placa
        if "eliminar" in form_response:

            cmd = f""" INSERT INTO InfoMiembrosInactivos SELECT * FROM InfoMiembros WHERE IdMember = {self.session['user']['IdMember']};
                       DELETE FROM InfoMiembros WHERE IdMember = {self.session['user']['IdMember']};
                       UPDATE InfoPlacas SET IdMember_FK = 0 WHERE IdMember_FK = {self.session['user']['IdMember']}
                    """
            self.db.cursor.executescript(cmd)

            # send email to cancelled user
            send_instant_email.send_cancel(
                correo=self.session["user"]["Correo"],
                nombre=self.session["user"]["NombreCompleto"],
            )

            self.log(
                message=f"Eliminado {self.session['user']['CodMember']} | {self.session['user']['NombreCompleto']} | {self.session['user']['DocNum']} | {self.session['user']['Correo']}"
            )
            return redirect("logout")

        # no errors
        if not any(errors.values()):

            if not changes_made:
                # no processing
                flash("No se realizaron cambios. ", "warning")

            else:
                # update member information

                # if user made changes to placas, update next message to be sent to tomorrow, else leave blank
                _update_next_message_send = (
                    f", NextMessageSend = '{(dt.now() + td(days=1)).strftime("%Y-%m-%d %H:%M:%S")}' "
                    if "Placas" in changes_made
                    else ""
                )
                self.db.cursor.execute(
                    f"""    UPDATE InfoMiembros SET
                            NombreCompleto = '{form_response["nombre"]}',
                            DocNum = '{form_response["dni"]}',
                            Celular = '{form_response["celular"]}'
                            {_update_next_message_send}
                            WHERE IdMember = {self.session['user']['IdMember']}"""
                )

                # update constraseña if changed
                if "Contraseña" in changes_made:
                    self.db.cursor.execute(
                        f"""    UPDATE InfoMiembros SET Password = '{form_response["contra2"]}'
                                WHERE IdMember = {self.session['user']['IdMember']}"""
                    )

                _ph = "2020-01-01"  # default placeholder value for date of last scrape for new placas

                # erase foreign key linking placa to member
                self.db.cursor.execute(
                    f"UPDATE InfoPlacas SET IdMember_FK = 0 WHERE IdMember_FK = {self.session['user']['IdMember']}"
                )

                # loop all non-empty placas and link foreign key to member if placa exists or create new placa record
                for placa in [i for i in placas if i]:

                    self.db.cursor.execute(
                        f"SELECT * FROM InfoPlacas WHERE Placa = '{placa.upper()}'"
                    )
                    if len(self.db.cursor.fetchall()) > 0:
                        # placa already exists in the database, assign foreign key to member
                        self.db.cursor.execute(
                            f"UPDATE InfoPlacas SET IdMember_FK = {self.session['user']['IdMember']} WHERE Placa = '{placa}'"
                        )
                    else:
                        # create new record
                        self.db.cursor.execute(
                            "SELECT IdPlaca FROM InfoPlacas ORDER BY IdPlaca DESC"
                        )
                        rec = int(self.db.cursor.fetchone()["IdPlaca"]) + 1
                        self.db.cursor.execute(
                            f"INSERT INTO InfoPlacas VALUES ({rec}, {self.session['user']['IdMember']}, '{placa}', '{_ph}', '{_ph}', '{_ph}', '{_ph}', '{_ph}')"
                        )

                self.db.conn.commit()
                flash(changes_made, "success")
                self.log(
                    message=f"Actualizado {self.session['user']['CodMember']} | {self.session['user']['NombreCompleto']} | {self.session['user']['DocNum']} | {self.session['user']['Correo']}"
                )

    return render_template(
        "cuenta-mis-datos-1.html",
        user=user,
        placas=placas,
        sgte_boletin=sgte_boletin,
        errors=errors,
    )


def load_member(db, correo):
    # gathering user data header
    db.cursor.execute(f"SELECT * FROM InfoMiembros WHERE Correo = '{correo}'")
    user = db.cursor.fetchone()
    return {user.keys()[n]: user[n] for n in range(13)}
