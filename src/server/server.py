import os
import sqlite3
import threading
import time
import base64
from datetime import datetime as dt
from flask import session, redirect, render_template, url_for, Response
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
from jinja2 import Environment, ext

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
    perfil as maq_mi_perfil,
    servicios as maq_mis_servicios,
    eliminar as maq_eliminar_registro,
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

        self.app.jinja_env.add_extension("jinja2.ext.do")

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

        # Load plates (placas)
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

    def descargar_archivo(self, tipo, id):
        # 1. Retrieve the base64/byte string from the database
        cursor = self.db.cursor()
        cmd = f"SELECT ImageBytes FROM {tipo} WHERE {'IdMember_FK' if "Records" in tipo else 'PlacaValidate'} = ?"
        cursor.execute(cmd, (id,))
        base64_string = cursor.fetchone()

        if not base64_string:
            return "File not found.", 404

        try:
            # 2. Decode the base64 string back into raw JPEG bytes
            image_bytes = base64.b64decode(base64_string["ImageBytes"])

            # 3. Create a descriptive file name
            if tipo == "DataApesegSoats":
                filename = f"Certificado SOAT {id}.jpg"
            elif tipo == "DataSunarpFichas":
                filename = f"Ficha SUNARP {id}.jpg"
            elif tipo == "DataMtcRecordsConductores":
                filename = f"Record Conductor {id}.pdf"
            else:
                filename = f"download_{tipo}_{id}.jpg"

            # --- Alternative using Flask Response ---
            response = Response(image_bytes, mimetype="image/jpeg")
            response.headers["Content-Disposition"] = (
                f'attachment; filename="{filename}"'
            )
            return response

        except KeyboardInterrupt:  # Exception as e:
            print(f"Error during file download for {tipo}/{id}")
            return "Error processing file.", 500

    def acerca_de(self):
        return acerca_de.main(self)

    def logout(self):
        session.clear()
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
        # self.session.clear()
        return maq_login.main(self)

    def maquinarias_registro(self):
        return maq_registro.main(self)

    def maquinarias_mis_servicios(self):
        cursor = self.db.cursor()
        return maq_mis_servicios.main(
            cursor=cursor, correo=session["usuario"]["correo"]
        )

    def maquinarias_eliminar_cuenta(self):
        return maq_eliminar_registro.main(self)

    def maquinarias_mi_perfil(self):
        return maq_mi_perfil.main(self)

    def maquinarias_logout(self):
        return redirect(url_for("maquinarias"))

    def nuevo_password(self):
        return "Nuievo PAss"

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
        user_info = token.get("userinfo")  # Get user info once
        cursor = self.db.cursor()
        correo = user_info["email"]

        activo = maq_login.validar_activacion(cursor, correo)
        if not activo:
            self.session["auth_error"] = {
                "email": correo,
                "provider": "Google",
                "name": token.get("name", "Usuario"),  # <-- ADDED 'name' HERE
            }
            return redirect(url_for("maquinarias"))

        suscrito = maq_login.validar_suscripcion(cursor, token.get("userinfo")["email"])
        if not suscrito:
            session["usuario"] = {"correo": token.get("userinfo")["email"]}
            session["password_only"] = False
            session["third_party_login"] = True
            return redirect("/maquinarias/registro")
        else:
            maq_login.extraer_data_usuario(
                cursor, correo=token.get("userinfo")["email"]
            )
            return maq_mis_servicios.main(cursor, correo=correo)

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
    #                OAUTH — APPLE, MICROSOFT, INSTAGRAM
    # ======================================================

    def apple_login(self):
        """Placeholder for future Apple OAuth."""
        pass

    def apple_authorize(self):
        """Placeholder for future Apple OAuth callback."""
        pass

    def microsoft_login(self):
        """Initiates the Microsoft OAuth login flow."""
        redirect_uri = url_for("microsoft_authorize", _external=True)
        return self.oauth.microsoft.authorize_redirect(redirect_uri)

    def microsoft_authorize(self):
        """Handles the callback after Microsoft OAuth authorization."""
        try:
            # 1. Authorize access token
            token = self.oauth.microsoft.authorize_access_token()

            # 2. Fetch user information (using the common 'me' endpoint for OpenID Connect)
            # Microsoft's user info can be retrieved from the id_token if configured,
            # or a specific endpoint. Using 'id_token' parsing is safer if properly set up.
            user_info = self.oauth.microsoft.parse_id_token(token)

            # Assuming user_info contains 'email' and 'name'
            user_email = user_info.get("email")
            user_name = user_info.get("name")

            # 3. Load user data or redirect to registration
            if user_email and self.load_user_data_into_session(user_email):
                # Login successful, user data loaded into session
                return redirect("/mis-datos")
            elif user_email:
                # User not found in database, redirect to registration
                return render_template(
                    "ui-registro-1.html",
                    errors={},
                    user={"correo": user_email, "nombre": user_name},
                )
            else:
                # Failed to get email from user_info
                return redirect(url_for("login"))

        except Exception as e:
            print("Microsoft Authorization Error:", e)
            return redirect(url_for("login"))

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
