from datetime import datetime as dt
from flask import redirect, request, render_template, url_for
from src.utils.constants import GOOGLE_CLIENT_ID, GOOGLE_CALLBACK_URI
from src.utils.utils import compare_text_to_hash


def main(self):

    # Session should expire naturally through PERMANENT_SESSION_LIFETIME
    self.session.permanent = True

    # HEAD request (robots, uptime checks)
    if request.method == "HEAD":
        return ("", 200)

    # If already logged in → go to user account
    if self.session.get("loaded_user"):
        return redirect(url_for("cuenta-mis-datos"))

    # GET → load the login page
    if request.method == "GET":
        return render_template(
            "ui-login.html",
            user={},
            errors={},
            google_client_id=GOOGLE_CLIENT_ID,
            google_callback_uri=GOOGLE_CALLBACK_URI,
        )

    # POST → user submitted login form
    form = dict(request.form)
    errors = validation(self.db, form)

    if not any(errors.values()):
        # LOGIN SUCCESS
        correo = form["correo"].lower()

        # Update login info
        cur = self.db.cursor()
        cur.execute(
            "UPDATE InfoMiembros SET LastLoginDatetime = ?, CountFailedLogins = 0 WHERE Correo = ?",
            (dt.now().strftime("%Y-%m-%d %H:%M:%S"), correo),
        )
        self.db.commit()

        # Log the event
        self.log(message=f"Login {correo}")

        # Load user into session
        self.load_user_data_into_session(correo)

        return redirect("mis-datos")

    # LOGIN FAILED
    else:
        # Increase failed login count
        cur = self.db.cursor()
        cur.execute(
            "UPDATE InfoMiembros SET CountFailedLogins = CountFailedLogins + 1 WHERE Correo = ?",
            (form["correo"],),
        )
        self.db.commit()

        # Log the failed attempt (do NOT log the password!)
        self.log(message=f"Unsuccessful Login Attempt ({form['correo']})")

        # Reset password field for safety
        if "password" in form:
            form["password"] = ""

        return render_template(
            "ui-login.html",
            user=form,
            errors=errors,
            google_client_id=GOOGLE_CLIENT_ID,
            google_callback_uri=GOOGLE_CALLBACK_URI,
        )


def validation(db, form):

    errors = {"correo": [], "password": [], "intentos": []}

    # Does the email exist?
    cur = db.cursor()
    cur.execute("SELECT Password FROM InfoMiembros WHERE Correo = ?", (form["correo"],))
    row = cur.fetchone()

    if not row:
        errors["correo"].append("Correo no registrado")
        return errors

    stored_hash = row[0]

    # Is the password correct?
    if not compare_text_to_hash(form["password"], stored_hash):
        errors["password"].append("Contraseña equivocada")

    # TODO: Add lockout logic here if needed

    return errors
