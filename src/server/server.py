import os
import sqlite3
import threading
import time
import base64
from datetime import datetime as dt, timedelta as td
from flask import session, redirect, render_template, url_for, Response, flash
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
from authlib.common.errors import AuthlibBaseError
import requests.exceptions
from jinja2 import Environment, ext
import uuid

# Local imports
from src.server import settings, updater, api, admin

# from src.ui import (
#     login,
#     mis_vencimientos,
#     registro,
#     recuperar,
#     logout,
#     mis_datos,
#     acerca_de,
# )
from src.ui.maquinarias import (
    login as maq_login,
    registro as maq_registro,
    perfil as maq_mi_perfil,
    servicios as maq_mis_servicios,
    eliminar as maq_eliminar_registro,
    recuperar as maq_recuperar,
)
from src.utils.constants import DB_NETWORK_PATH
from src.comms import enviar_correo_inmediato


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
            # self.conn.execute("PRAGMA journal_mode=WAL")
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

    # ======================================================
    #                        UI ROUTES
    # ======================================================

    def root(self):
        return redirect(url_for("maquinarias"))

    def descargar_archivo(self, tipo, id):

        # seguridad: evitar navegacion directa a url
        if session.get("etapa") != "validado":
            return redirect(url_for("maquinarias"))

        # 1. Retrieve the base64/byte string from the database
        cursor = self.db.cursor()
        cmd = f"SELECT ImageBytes FROM {tipo} WHERE {'IdMember_FK' if "Records" in tipo else 'PlacaValidate'} = ?"
        cursor.execute(cmd, (id,))
        base64_string = cursor.fetchone()

        if not base64_string:
            return "No se encontro archivo.", 404

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

            response = Response(image_bytes, mimetype="image/jpeg")
            response.headers["Content-Disposition"] = (
                f'attachment; filename="{filename}"'
            )
            return response

        except Exception as e:
            return f"Error procesando archivo: {e}.", 500

    def logout(self):
        session.clear()
        return redirect(url_for("maquinarias"))

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

    def maquinarias_mis_servicios(self):
        return maq_mis_servicios.main(self)

    def maquinarias_eliminar_cuenta(self):
        return maq_eliminar_registro.main(self)

    def maquinarias_mi_perfil(self):
        return maq_mi_perfil.main(self)

    def maquinarias_logout(self):
        session.clear()
        return redirect(url_for("maquinarias"))

    def maquinarias_tyc(self):
        return render_template("ui-maquinarias-terminos-y-condiciones.html")

    def maquinarias_pdp(self):
        return render_template("ui-maquinarias-politica-de-privacidad.html")

    def nuevo_password(self):
        # generar password alfanumerico al azar
        token = uuid.uuid4().hex
        cursor = self.db.cursor()
        correo = session["usuario"]["correo"]
        id_member = session["usuario"]["id_member"]

        # actualizar base de datos
        cmd = """
                    INSERT INTO StatusTokens 
                    (IdMember, TokenHash, TokenTipo, Correo, FechaHasta, TokenUsado)
                    VALUES 
                    (?, ?, ?, ?, ?, ?)
                """
        cursor.execute(
            cmd, (id_member, token, "Password", correo, dt.now() + td(minutes=10), 0)
        )
        self.db.conn.commit()

        # mandar correo
        enviar_correo_inmediato.recuperacion_contrasena(
            self.db,
            correo=correo,
            token=token,
        )
        flash(f"Hemos enviado un correo a {correo}.")

        return redirect(url_for("maquinarias"))

    def recuperar_contrasena(self, token):
        return maq_recuperar.main(self, token)

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
    #           OAUTH (Activos) — Google, Facebook
    # ======================================================

    def google_login(self):
        redirect_uri = url_for("google_authorize", _external=True)
        return self.oauth.google.authorize_redirect(redirect_uri)

    def google_authorize(self):
        try:
            token = self.oauth.google.authorize_access_token()
            correo = token.get("userinfo")["email"]
            nombre = token.get("name", "Usuario")
            return self.terminar_login_terceros(correo, nombre, proveedor="Google")
        except (AuthlibBaseError, requests.exceptions.RequestException):
            flash("Error de credenciales.")
            return redirect(url_for("maquinarias"))
        except Exception as e:
            flash(f"Error general: {e}. Intente otra vez.")
            return redirect(url_for("maquinarias"))
        # except KeyboardInterrupt:
        #     pass

    def facebook_login(self):
        redirect_uri = url_for("facebook_authorize", _external=True)
        return self.oauth.facebook.authorize_redirect(redirect_uri)

    def facebook_authorize(self):
        try:
            self.oauth.facebook.authorize_access_token()
            profile = self.oauth.facebook.get("me?fields=id,name,email").json()
            correo = profile.get("email")
            nombre = profile.get("name")
            return self.terminar_login_terceros(correo, nombre, proveedor="Facebook")
        except (AuthlibBaseError, requests.exceptions.RequestException):
            flash("Error de credenciales.")
            return redirect(url_for("maquinarias"))
        except Exception as e:
            flash(f"Error general: {e}. Intente otra vez.")
            return redirect(url_for("maquinarias"))

    def terminar_login_terceros(self, correo, nombre, proveedor):

        cursor = self.db.cursor()

        # revisar si miembro activo -- si no, popup advirtiendo y regresa
        activo = maq_login.validar_activacion(cursor, correo)
        if not activo:
            self.session["auth_error"] = {
                "email": correo,
                "provider": proveedor,
                "name": nombre,
            }
            return redirect(url_for("maquinarias"))

        # revisar si miembro suscrito -- si no, flujo de registro antes
        suscrito = maq_login.validar_suscripcion(cursor, correo)
        if not suscrito:
            session["usuario"] = {"correo": correo}
            session["password_only"] = False
            session["third_party_login"] = True
            session["etapa"] = "registro"
            return redirect("/maquinarias/registro")
        else:
            maq_login.extraer_data_usuario(cursor, correo=correo)
            session["etapa"] = "validado"
            return maq_mis_servicios.main(self)

    # ======================================================
    #     OAUTH (Pendientes) — APPLE, MICROSOFT, INSTAGRAM
    # ======================================================

    def microsoft_login(self):
        redirect_uri = url_for("microsoft_authorize", _external=True)
        return self.oauth.microsoft.authorize_redirect(redirect_uri)

    def microsoft_authorize(self):
        try:
            token = self.oauth.microsoft.authorize_access_token()
            user_info = self.oauth.microsoft.parse_id_token(token)
            correo = user_info.get("email")
            nombre = user_info.get("name")
            return self.terminar_login_terceros(correo, nombre, proveedor="Facebook")
        except (AuthlibBaseError, requests.exceptions.RequestException):
            flash("Error de credenciales.")
            return redirect(url_for("maquinarias"))
        except Exception as e:
            flash(f"Error general: {e}. Intente otra vez.")
            return redirect(url_for("maquinarias"))

    def instagram_login(self):
        """Placeholder for future Instagram OAuth."""
        pass

    def instagram_authorize(self):
        """Placeholder for future Instagram OAuth callback."""
        pass

    def apple_login(self):
        """Placeholder for future Apple OAuth."""
        pass

    def apple_authorize(self):
        """Placeholder for future Apple OAuth callback."""
        pass
