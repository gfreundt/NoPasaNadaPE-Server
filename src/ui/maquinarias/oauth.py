import requests
import logging
from flask import current_app, session, redirect, url_for, flash
from authlib.common.errors import AuthlibBaseError
import requests.exceptions

from src.ui.maquinarias import login, mis_servicios

logger = logging.getLogger(__name__)

# =========================================================
#       Activos: GOOGLE, FACEBOOK
# =========================================================


def google_login():
    """
    Punto de entrada para login con Google.
    Redirige a Google para autenticación.
    """
    redirect_uri = url_for("google_authorize", _external=True)
    return current_app.oauth.google.authorize_redirect(redirect_uri)


def google_authorize():
    """
    Callback de Google después de autenticación.
    Procesa respuesta de Google, obtiene correo y nombre, y termina login.
    """
    try:
        token = current_app.oauth.google.authorize_access_token()
        correo = token.get("userinfo")["email"]
        nombre = token.get("name", "Usuario")
        logger.info(f"Login exitoso de Google para correo: {correo}")
        return terminar_login_terceros(correo, nombre, proveedor="Google")

    except (AuthlibBaseError, requests.exceptions.RequestException):
        logger.exception("Error de credenciales en login de Google")
        return redirect(url_for("maquinarias-login"))

    except Exception as e:
        logger.exception("Error general en autorización de Google")
        return redirect(url_for("maquinarias-login"))


def facebook_login():
    """
    Punto de entrada para login con Facebook.
    Redirige a Facebook para autenticación.
    """
    redirect_uri = url_for("facebook_authorize", _external=True)
    return current_app.oauth.facebook.authorize_redirect(redirect_uri)


def facebook_authorize():
    """
    Callback de Facebook después de autenticación.
    Procesa respuesta de Facebook, obtiene correo y nombre, y termina login.
    """
    try:
        current_app.oauth.facebook.authorize_access_token()
        profile = current_app.oauth.facebook.get("me?fields=id,name,email").json()
        correo = profile.get("email")
        nombre = profile.get("name")
        return terminar_login_terceros(correo, nombre, proveedor="Facebook")

    except (AuthlibBaseError, requests.exceptions.RequestException):
        logger.exception("Error de credenciales en login de Facebook")
        return redirect(url_for("maquinarias-login"))

    except Exception as e:
        logger.exception("Error general en autorización de Facebook")
        return redirect(url_for("maquinarias-login"))


def terminar_login_terceros(correo, nombre, proveedor):
    """
    Una vez autenticado por tercero, determina si usuario es valido en nuestro sistema.
    Si esta autorizado pero no inscrito, redirige a registro.
    Si esta autorizado e inscrito, redirige a mis servicios.
    """

    # revisar si miembro autorizado -- si no, popup advirtiendo y regresa
    activo = login.validar_activacion(cursor=current_app.db.cursor(), correo=correo)
    if not activo:
        session["auth_error"] = {
            "email": correo,
            "provider": proveedor,
            "name": nombre,
        }
        return redirect(url_for("maquinarias-login"))

    # revisar si miembro suscrito -- si no, flujo de registro antes
    session["usuario"] = {"correo": correo}
    suscrito = login.validar_suscripcion(cursor=current_app.db.cursor(), correo=correo)
    if not suscrito:
        session["password_only"] = False
        session["third_party_login"] = True
        session["etapa"] = "registro"
        return redirect("/maquinarias/registro")
    else:
        session["etapa"] = "validado"
        return mis_servicios.main()


# =========================================================
#       Pendientes: APPLE, MICROSOFT, INSTAGRAM
# =========================================================


def microsoft_login(app):
    redirect_uri = url_for("microsoft_authorize", _external=True)
    return app.oauth.microsoft.authorize_redirect(redirect_uri)


def microsoft_authorize(app):
    try:
        token = app.oauth.microsoft.authorize_access_token()
        user_info = app.oauth.microsoft.parse_id_token(token)
        correo = user_info.get("email")
        nombre = user_info.get("name")
        return app.terminar_login_terceros(correo, nombre, proveedor="Facebook")
    except (AuthlibBaseError, requests.exceptions.RequestException):
        flash("Error de credenciales.")
        return redirect(url_for("maquinarias-login"))
    except Exception as e:
        flash(f"Error general: {e}. Intente otra vez.")
        return redirect(url_for("maquinarias-login"))


def instagram_login(app):
    """Placeholder for future Instagram OAuth."""
    pass


def instagram_authorize(app):
    """Placeholder for future Instagram OAuth callback."""
    pass


def apple_login(app):
    """Placeholder for future Apple OAuth."""
    pass


def apple_authorize(app):
    """Placeholder for future Apple OAuth callback."""
    pass
