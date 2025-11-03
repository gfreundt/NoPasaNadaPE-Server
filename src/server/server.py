from functools import wraps
from flask import request, session, redirect, render_template
import threading
from datetime import datetime as dt
import time

# local imports
from src.utils.utils import get_local_ip
from src.server import settings, oauth, updater, api
from src.ui import (
    login,
    mis_vencimientos,
    registro,
    recuperar,
    logout,
    mis_datos,
    acerca_de,
)


# decorator function: default to login page if user not logged in
def logged_in(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user" not in session and "login_correo" not in session:
            return redirect("login")
        return func(*args, **kwargs)

    return wrapper


class Server:

    def __init__(self, db, app):

        self.db = db
        self.data_lock = threading.Lock()

        # initialize Flask app object, set configuration and define routes
        self.app = app
        self.session = session

        # set app configurations and define endpoints
        settings.set_config(self)
        settings.set_routes(self)

        # init page counter for endpoints
        self.page = 0

    # starting server
    def run(self):
        print(f" > SERVER RUNNING ON: http://{get_local_ip()}:5000")
        self.app.run(
            debug=False,
            threaded=True,
            port=5000,
            host="0.0.0.0",
        )

    def run_in_background(self):
        flask_thread = threading.Thread(target=self.run, daemon=True)
        flask_thread.start()
        return flask_thread

    def log(self, **kwargs):
        if not kwargs.get("type"):
            kwargs["type"] = "0"
        self.db.cursor.execute(
            "INSERT INTO StatusLogs VALUES (?,?,?)",
            (kwargs["type"], kwargs["message"], str(dt.now())),
        )

    def load_user_data_into_session(self, correo):
        # get user data from database
        self.db.cursor.execute(
            "SELECT * FROM InfoMiembros WHERE Correo = ?",
            (correo,),
        )
        self.session["loaded_user"] = dict(self.db.cursor.fetchone())

        # get placa data for this user from database
        self.db.cursor.execute(
            "SELECT * FROM InfoPlacas WHERE IdMember_FK = ?",
            (self.session["loaded_user"]["IdMember"],),
        )
        self.loaded_placas = {
            f"placa{j}": i["Placa"]
            for j, i in enumerate(self.db.cursor.fetchall(), start=1)
        }

    # FRONT END ENDPOINTS
    @logged_in
    def root(self):
        return login.main(self)

    def login(self):
        if request.method == "HEAD":
            return ("", 200)
        return login.main(self)

    def registro(self):
        return registro.main(self)

    def recuperar(self):
        return recuperar.main(self)

    # --- navbar
    @logged_in
    def mis_datos(self):
        return mis_datos.main(self)

    @logged_in
    def mis_vencimientos(self):
        return mis_vencimientos.main(self)

    def acerca_de(self):
        return acerca_de.main(self)

    def logout(self):
        return logout.main(self)

    # --- direct links
    def rnt(self):
        return render_template("ui-rnt.html")

    def tyc(self):
        return render_template("ui-terminos-y-condiciones.html")

    def pdp(self):
        return render_template("ui-politica-de-privacidad.html")

    def maquinarias(self):
        return render_template("ui-landing-maquinarias.html")

    # BACKEND ENDPOINTS
    def update(self):
        return updater.update(self)

    def api_request(self, version):
        timer_start = time.perf_counter()
        return api.version_select(self, version, timer_start)

    # redirect endpoint (OAuth)
    def redir(self):
        self.all_params = request.args.to_dict()
        oauth.get_oauth2_token(self)


# TODO: oauth still work in progress
