import os
import sqlite3
import threading
import time
from datetime import datetime as dt
from flask import session, redirect, render_template, url_for
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token

# Local imports
from src.server import settings, updater, api, admin
from src.ui import (
    login,
    mis_vencimientos,
    registro,
    recuperar,
    logout,
    mis_datos,
    acerca_de,
)
from src.ui.maquinarias import (
    login as maq_login,
    registro as maq_registro,
)
from src.utils.constants import DB_NETWORK_PATH, NETWORK_PATH

# from ui.maquinarias import data_servicios as maq_mi_cuenta


# ============================================================
#                      DATABASE LAYER
# ============================================================


class Database:
    def __init__(self):
        self.conn = None
        self._pid = None

    def _ensure_conn(self):
        """Ensures each worker has its own SQLite connection."""
        current_pid = os.getpid()

        if self.conn is None or self._pid != current_pid:
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass

            self.conn = sqlite3.connect(
                DB_NETWORK_PATH,
                check_same_thread=False,
                timeout=5.0,
            )
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self._pid = current_pid

    def cursor(self):
        self._ensure_conn()
        return self.conn.cursor()

    def commit(self):
        self._ensure_conn()
        self.conn.commit()

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
            self._pid = None


# ============================================================
#                      MAIN SERVER CLASS
# ============================================================


class Server:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.data_lock = threading.Lock()

        # Flask config + routes + OAuth
        settings.set_flask_config(self)
        settings.set_routes(self)

        self.oauth = OAuth(app)
        settings.set_oauth_config(self)

        self.session = session
        self.page = 0

    # ======================================================
    #                   DATABASE OPERATIONS
    # ======================================================

    def log(self, **kwargs):
        """Insert a status log entry into the database."""
        if not kwargs.get("type"):
            kwargs["type"] = "0"

        cur = self.db.cursor()
        cur.execute(
            "INSERT INTO StatusLogs VALUES (?,?,?)",
            (kwargs["type"], kwargs["message"], str(dt.now())),
        )
        self.db.commit()

    def load_user_data_into_session(self, correo):
        """Load user account + associated plates into session."""

        cur = self.db.cursor()
        cur.execute("SELECT * FROM InfoMiembros WHERE Correo = ?", (correo,))
        user_row = cur.fetchone()

        if not user_row:
            return False

        # Save base user data
        self.session["loaded_user"] = dict(user_row)

        # Load placas
        cur = self.db.cursor()
        cur.execute(
            "SELECT * FROM InfoPlacas WHERE IdMember_FK = ?",
            (self.session["loaded_user"]["IdMember"],),
        )
        placas = cur.fetchall()

        self.session["loaded_user"]["Placas"] = {
            f"placa{j}": i["Placa"] for j, i in enumerate(placas, start=1)
        }

        return True

    # ======================================================
    #                        UI ROUTES
    # ======================================================

    def root(self):
        return redirect(url_for("maquinarias"))

    def login(self):
        return login.main(self)

    def registro(self):
        return registro.main(self)

    def recuperar(self):
        return recuperar.main(self)

    def mis_datos(self):
        return mis_datos.main(self)

    def mis_vencimientos(self):
        return mis_vencimientos.main(self)

    def acerca_de(self):
        return acerca_de.main(self)

    def logout(self):
        return logout.main(self)

    # Direct UI Pages
    def rnt(self):
        return render_template("ui-rnt.html")

    def tyc(self):
        return render_template("ui-terminos-y-condiciones.html")

    def pdp(self):
        return render_template("ui-politica-de-privacidad.html")

    # Maquinarias
    def maquinarias(self):
        return maq_login.main(self)

    def maquinarias_registro(self):
        return maq_registro.main(self)

    def maquinarias_mi_cuenta(self):
        return maq_mi_cuenta.main(self)

    # ======================================================
    #                      BACKEND APIs
    # ======================================================

    def update(self):
        return updater.update(self)

    def api_externo(self, version):
        timer_start = time.perf_counter()
        return api.version_select(self, version, timer_start)

    def api_admin(self):
        return admin.main(self)

    # ======================================================
    #                 OAUTH — GOOGLE, FB, LINKEDIN
    # ======================================================

    def google_login(self):
        redirect_uri = url_for("google_authorize", _external=True)
        return self.oauth.google.authorize_redirect(redirect_uri)

    def google_authorize(self):
        token = self.oauth.google.authorize_access_token()
        user_info = token.get("userinfo")

        if not self.load_user_data_into_session(user_info["email"]):
            return render_template(
                "ui-registro-1.html",
                errors={},
                user={"correo": user_info["email"], "nombre": user_info["name"]},
            )

        return redirect("/mis-datos")

    def facebook_login(self):
        redirect_uri = url_for("facebook_authorize", _external=True)
        return self.oauth.facebook.authorize_redirect(redirect_uri)

    def facebook_authorize(self):
        try:
            token = self.oauth.facebook.authorize_access_token()
        except Exception:
            return redirect(url_for("ui-login"))

        user_resp = self.oauth.facebook.get("me?fields=id,name,email")
        user_info = user_resp.json()

        print("Facebook login:", user_info.get("email"))
        return redirect(url_for("dashboard"))

    def linkedin_login(self):
        redirect_uri = url_for("linkedin_authorize", _external=True)
        nonce_value = generate_token()
        session["oauth_nonce"] = nonce_value

        return self.oauth.linkedin.authorize_redirect(redirect_uri, nonce=nonce_value)

    def linkedin_authorize(self):
        try:
            token = self.oauth.linkedin.authorize_access_token()
            user_info = self.oauth.linkedin.parse_id_token(token)

            user_email = user_info.get("email")
            user_name = user_info.get("name")

            if user_email:
                session.permanent = True
                session["user"] = {
                    "email": user_email,
                    "name": user_name,
                    "provider": "LinkedIn",
                }

            return redirect(url_for("ui-root"))

        except Exception as e:
            print("LinkedIn Authorization Error:", e)
            return redirect(url_for("ui-login"))

    # ======================================================
    #                OAUTH PLACEHOLDERS (RESTORED)
    # ======================================================

    def apple_login(self):
        """Placeholder for future Apple OAuth."""
        pass

    def apple_authorize(self):
        """Placeholder for future Apple OAuth callback."""
        pass

    def microsoft_login(self):
        """Placeholder for future Microsoft OAuth."""
        pass

    def microsoft_authorize(self):
        """Placeholder for future Microsoft OAuth callback."""
        pass

    def instagram_login(self):
        """Placeholder for future Instagram OAuth."""
        pass

    def instagram_authorize(self):
        """Placeholder for future Instagram OAuth callback."""
        pass

    # ======================================================
    #                MAQUINARIAS GOOGLE OAUTH
    # ======================================================

    def maq_google_login(self):
        redirect_uri = url_for("maq_google_authorize", _external=True)
        return self.oauth.google.authorize_redirect(redirect_uri)

    def maq_google_authorize(self):
        token = self.oauth.google.authorize_access_token()
        user_info = token.get("userinfo")

        if not self.load_user_data_into_session(user_info["email"]):
            return render_template(
                "ui-registro-1.html",
                errors={},
                user={"correo": user_info["email"], "nombre": user_info["name"]},
            )

        return redirect("/mis-datos")
