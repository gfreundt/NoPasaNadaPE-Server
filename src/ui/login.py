from datetime import datetime as dt
from flask import redirect, request, render_template


# login endpoint
def main(self):

    # respuesta para solicitud de HEAD (robots revisando status de la pagina
    if request.method == "HEAD":
        return ("", 200)
    

    # cargando la data de la pagina
    if request.method == "GET":
        return render_template("ui-login.html", user={}, errors={})

    # recibir datos para intento de login
    elif request.method == "POST":
        form_response = dict(request.form)
        errors = validation(self.db, form_response)

        if not any(errors.values()):
            # gather user data header
            # update last login information
            self.db.cursor.executescript(
                f"""    UPDATE InfoMiembros SET LastLoginDatetime = '{dt.now().strftime("%Y-%m-%d %H:%M:%S")}' WHERE Correo = '{form_response["correo"].lower()}';
                        UPDATE InfoMiembros SET CountFailedLogins = 0 WHERE Correo = '{form_response["correo"].lower()}'
                 """
            )
            # log activity
            self.log(message=f"Login {form_response["correo"].lower()}")
            self.session["login_correo"] = form_response["correo"].lower()
            return redirect("mis-datos")

        else:
            # add one to failed login counter
            self.db.cursor.execute(
                f"UPDATE InfoMiembros SET CountFailedLogins = CountFailedLogins + 1 WHERE Correo = '{form_response['correo']}'"
            )
            # log activity
            self.log(
                message=f"Unsuccesful Login ({form_response['correo']} | {form_response['password']})"
            )
            # reset password field
            if "password" in form_response:
                form_response["password"] = ""
            return render_template("ui-login.html", user=form_response, errors=errors)


def validation(db, form_response):

    errors = {
        "correo": [],
        "password": [],
        "intentos": [],
    }

    # check if correo exists
    cmd = "SELECT * FROM InfoMiembros WHERE Correo = ?"
    db.cursor.execute(cmd, (form_response["correo"],))
    if not db.cursor.fetchone():
        errors.update({"correo": ["Correo no registrado"]})
        return errors

    # check if password correct for that correo
    cmd = "SELECT * FROM InfoMiembros WHERE Correo = ? AND Password = ?"
    db.cursor.execute(cmd, (form_response["correo"], form_response["password"]))
    if not db.cursor.fetchone():
        errors.update({"password": ["Contraseña equivocada"]})

    # TODO: check if exceeded login attempts

    return errors
