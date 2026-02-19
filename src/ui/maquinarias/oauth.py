import requests
from flask import current_app, session, redirect, url_for, flash
from authlib.common.errors import AuthlibBaseError
import requests.exceptions

from src.ui.maquinarias import login, mis_servicios

# =========================================================
#       Activos: GOOGLE, FACEBOOK
# =========================================================


def google_login():
    redirect_uri = url_for("google_authorize", _external=True)
    return current_app.oauth.google.authorize_redirect(redirect_uri)


def google_authorize():
    try:
        token = current_app.oauth.google.authorize_access_token()
        correo = token.get("userinfo")["email"]
        nombre = token.get("name", "Usuario")
        return terminar_login_terceros(correo, nombre, proveedor="Google")
    except (AuthlibBaseError, requests.exceptions.RequestException):
        flash("Error de credenciales.")
        return redirect(url_for("maquinarias"))
    except Exception as e:
        flash(f"Error general: {e}. Intente otra vez.")
        return redirect(url_for("maquinarias"))


def facebook_login():
    redirect_uri = url_for("facebook_authorize", _external=True)
    return current_app.oauth.facebook.authorize_redirect(redirect_uri)


def facebook_authorize():
    try:
        current_app.oauth.facebook.authorize_access_token()
        profile = current_app.oauth.facebook.get("me?fields=id,name,email").json()
        correo = profile.get("email")
        nombre = profile.get("name")
        return current_app.terminar_login_terceros(correo, nombre, proveedor="Facebook")
    except (AuthlibBaseError, requests.exceptions.RequestException):
        flash("Error de credenciales.")
        return redirect(url_for("maquinarias"))
    except Exception as e:
        flash(f"Error general: {e}. Intente otra vez.")
        return redirect(url_for("maquinarias"))


def terminar_login_terceros(correo, nombre, proveedor):
    # cursor = app.db.cursor()

    # revisar si miembro activo -- si no, popup advirtiendo y regresa
    activo = login.validar_activacion(correo)
    if not activo:
        session["auth_error"] = {
            "email": correo,
            "provider": proveedor,
            "name": nombre,
        }
        return redirect(url_for("maquinarias"))

    # revisar si miembro suscrito -- si no, flujo de registro antes
    suscrito = login.validar_suscripcion(correo)
    if not suscrito:
        session["usuario"] = {"correo": correo}
        session["password_only"] = False
        session["third_party_login"] = True
        session["etapa"] = "registro"
        return redirect("/maquinarias/registro")
    else:
        # login.extraer_data_usuario(cursor, correo=correo)
        session["etapa"] = "validado"
        return mis_servicios.main(current_app.db)


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
        return redirect(url_for("maquinarias"))
    except Exception as e:
        flash(f"Error general: {e}. Intente otra vez.")
        return redirect(url_for("maquinarias"))


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
