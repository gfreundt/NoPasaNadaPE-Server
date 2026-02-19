import time
import base64
from flask import session, redirect, render_template, url_for, Response, flash
from authlib.integrations.flask_client import OAuth
from authlib.common.errors import AuthlibBaseError
import requests.exceptions
import logging
from server import api_admin, api_externo
from src.server import autorizar_nueva_contrasena
from src.utils.constants import NETWORK_PATH
from src.server import settings
from src.ui.maquinarias import (
    login,
    registro,
    mi_perfil,
    eliminar,
    mis_servicios,
    cambiar_contrasena,
)


logger = logging.getLogger(__name__)


class Rutas:
    """
    Crea una clase que define las rutas de Flask y las funciones de cada ruta.
    """

    def __init__(self, db, app):
        self.db = db
        self.app = app

        # configuracion de flask y definicion de rutas
        settings.set_flask_config(self)
        settings.set_server_routes(self)

        # configuracion de OAuth para login con apps de terceros
        self.oauth = OAuth(app)
        settings.set_oauth_config(self)

        logger.info(f"Network Path: {NETWORK_PATH}")

        @app.errorhandler(Exception)
        def handle_exception(e):
            app.logger.exception("Error de Flask - No Manejada")
            return "Internal Server Error", 500

    # ======================================================
    #                  Front End GENERAL
    # ======================================================

    def root(self):
        return redirect(url_for("maquinarias"))

    def descargar_archivo(self, tipo, id):
        # seguridad: evitar navegacion directa a url
        if session.get("etapa") != "validado":
            return redirect(url_for("maquinarias"))

        # 1. Retrieve the base64/byte string from the database
        cursor = self.db.cursor()
        cmd = f"SELECT ImageBytes FROM {tipo} WHERE {'IdMember_FK' if 'Records' in tipo else 'PlacaValidate'} = ?"
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

    # ======================================================
    #                 Front End MAQUINARIAS
    # ======================================================

    def logout(self):
        logger.info(
            f"Logout: Id={session.get('id_member')} Correo={session.get('Correo')}"
        )
        session.clear()
        return redirect(url_for("maquinarias"))

    def rnt(self):
        return render_template("ui-rnt.html")

    def maquinarias_tyc_pdp(self):
        return render_template(
            "ui-maquinarias-terminos-y-condiciones-politica-de-privacidad.html"
        )

    def maquinarias_pduddp(self):
        return render_template(
            "ui-maquinarias-politica-de-uso-de-datos-personales.html"
        )

    def maquinarias(self):
        return login.main(self)

    def maquinarias_registro(self):
        return registro.main(self)

    def maquinarias_mis_servicios(self):
        return mis_servicios.main(self)

    def maquinarias_eliminar_cuenta(self):
        return eliminar.main(self)

    def maquinarias_mi_perfil(self):
        return mi_perfil.main(self)

    def maquinarias_logout(self):
        session.clear()
        return redirect(url_for("maquinarias"))

    def documentacion_api_v1(self):
        return render_template("ui-documentacion-api-v1.html")

    def autorizar_nueva_contrasena(self):
        return autorizar_nueva_contrasena.main(self)

    def recuperar_contrasena(self, token):
        return cambiar_contrasena.main(self, token)

    # ======================================================
    #                   Back End APIs
    # ======================================================

    def api_externo(self, version):
        timer_start = time.perf_counter()
        return api_externo.version_select(self, version, timer_start)

    def api_admin(self):
        return api_admin.main(self)

    # ======================================================
    #       Back End OAUTH (Activos) — Google, Facebook
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
        activo = login.validar_activacion(cursor, correo)
        if not activo:
            session["auth_error"] = {
                "email": correo,
                "provider": proveedor,
                "name": nombre,
            }
            return redirect(url_for("maquinarias"))

        # revisar si miembro suscrito -- si no, flujo de registro antes
        suscrito = login.validar_suscripcion(cursor, correo)
        if not suscrito:
            session["usuario"] = {"correo": correo}
            session["password_only"] = False
            session["third_party_login"] = True
            session["etapa"] = "registro"
            return redirect("/maquinarias/registro")
        else:
            login.extraer_data_usuario(cursor, correo=correo)
            session["etapa"] = "validado"
            return mis_servicios.main(self)

    # =========================================================
    # Back End OAUTH (Pendientes) — APPLE, MICROSOFT, INSTAGRAM
    # =========================================================

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
