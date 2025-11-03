from datetime import datetime as dt
from flask import redirect, request, render_template

from src.utils.utils import compare_text_to_hash


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

    # extract record information
    cmd = "SELECT Password FROM InfoMiembros WHERE Correo = ?"
    db.cursor.execute(cmd, (form_response["correo"],))
    user_record = db.cursor.fetchone()

    # check if correo exists
    if not user_record:
        errors.update({"correo": ["Correo no registrado"]})
        return errors

    # check if password correct for that correo
    if not compare_text_to_hash(text_string=form_response["password"], hash_string=user_record[0]):
        errors.update({"password": ["Contraseña equivocada"]})

    # TODO: check if exceeded login attempts

    return errors
