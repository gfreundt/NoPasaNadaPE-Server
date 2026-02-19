from datetime import timedelta as td
from flask import render_template
from werkzeug.exceptions import HTTPException
from authlib.integrations.flask_client import OAuth
from security.keys import (
    FLASK_SECRET_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    FACEBOOK_CLIENT_ID,
    FACEBOOK_CLIENT_SECRET,
    MICROSOFT_CLIENT_ID,
    MICROSOFT_CLIENT_SECRET,
)
from src.server import (
    autorizar_nueva_contrasena,
    descargar_archivo,
    api_admin,
    api_externo,
)
from src.ui.maquinarias import (
    login,
    registro,
    mi_perfil,
    eliminar,
    mis_servicios,
    cambiar_contrasena,
    logout,
    oauth,
)


def definir_rutas(app):

    # ------------- Landing
    app.add_url_rule(
        rule="/",
        endpoint="ui-root",
        view_func=login.main,
        methods=["GET", "POST", "HEAD"],
    )

    # ------------- Rutas UI (dinamicas)
    app.add_url_rule(
        rule="/maquinarias",
        endpoint="maquinarias",
        view_func=login.main,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/maquinarias/registro",
        endpoint="maquinarias-registro",
        view_func=registro.main,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/maquinarias/mi-cuenta",
        endpoint="maquinarias-mis-servicios",
        view_func=mis_servicios.main,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/maquinarias/eliminar-cuenta",
        endpoint="maquinarias-eliminar-cuenta",
        view_func=eliminar.main,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/maquinarias/mi-perfil",
        endpoint="maquinarias-mi-perfil",
        view_func=mi_perfil.main,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/nuevo_password",
        endpoint="autorizar_nueva_contrasena",
        view_func=autorizar_nueva_contrasena.main,
        methods=["GET"],
    )
    app.add_url_rule(
        rule="/recuperar-contrasena/<token>",
        endpoint="recuperar_contrasena",
        view_func=cambiar_contrasena.main,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/maquinarias/logout",
        endpoint="maquinarias_logout",
        view_func=logout.main,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/descargar_archivo/<tipo>/<id>",
        endpoint="maquinarias_descargar_archivo",
        view_func=descargar_archivo.main,
        methods=["GET"],
    )

    # ------------- Rutas UI (texto fijo)
    app.add_url_rule(
        rule="/maquinarias/terminos-y-condiciones-politica-de-privacidad",
        endpoint="terminos-y-condiciones-politica-de-privacidad",
        view_func=lambda: render_template(
            "ui-maquinarias-terminos-y-condiciones-politica-de-privacidad.html"
        ),
        methods=["GET"],
    )
    app.add_url_rule(
        rule="/maquinarias/politica-de-uso-de-datos-personales",
        endpoint="politica-de-uso-de-datos-personales",
        view_func=lambda: render_template(
            "ui-maquinarias-politica-de-uso-de-datos-personales.html"
        ),
        methods=["GET"],
    )
    app.add_url_rule(
        rule="/documentacion-api-v1",
        endpoint="documentacion-api-v1",
        view_func=lambda: render_template("ui-documentacion-api-v1.html"),
        methods=["GET"],
    )
    app.add_url_rule(
        rule="/reglamento-nacional-de-transito",
        endpoint="rnt",
        view_func=lambda: render_template("reglamento-nacional-de-transito.html"),
        methods=["GET"],
    )

    # ------------- Rutas Back-End

    # APIs
    app.add_url_rule(
        rule="/api/<version>",
        endpoint="api_version",
        view_func=api_externo,
        methods=["POST"],
    )
    app.add_url_rule(
        rule="/admin",
        endpoint="admin",
        view_func=api_admin,
        methods=["POST"],
    )

    # Login de terceros
    app.add_url_rule(
        rule="/google_login",
        endpoint="google_login",
        view_func=oauth.google_login,
    )
    app.add_url_rule(
        rule="/google_callback",
        endpoint="google_authorize",
        view_func=oauth.google_authorize,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/facebook_login",
        endpoint="facebook_login",
        view_func=oauth.facebook_login,
    )
    app.add_url_rule(
        rule="/facebook_callback",
        endpoint="facebook_authorize",
        view_func=oauth.facebook_authorize,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/instagram_login",
        endpoint="instagram_login",
        view_func=oauth.instagram_login,
    )
    app.add_url_rule(
        rule="/instagram_callback",
        endpoint="instagram_authorize",
        view_func=oauth.instagram_authorize,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/microsoft_login",
        endpoint="microsoft_login",
        view_func=oauth.microsoft_login,
    )
    app.add_url_rule(
        rule="/microsoft_callback",
        endpoint="microsoft_authorize",
        view_func=oauth.microsoft_authorize,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        rule="/apple_login",
        endpoint="apple_login",
        view_func=oauth.apple_login,
    )
    app.add_url_rule(
        rule="/apple_callback",
        endpoint="apple_authorize",
        view_func=oauth.apple_authorize,
        methods=["GET", "POST"],
    )


def configurar_flask(app):
    app.jinja_env.add_extension("jinja2.ext.do")
    app.secret_key = FLASK_SECRET_KEY
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = td(minutes=10)
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_SAMESITE=None,  # <-- Important: allow external redirect from Google
    )
    app.config["SESSION_COOKIE_DOMAIN"] = None

    # --- Manejo de Errores ---
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return e.description, e.code

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.exception("\nError de Flask - No Manejada")
        return "Internal Server Error", 500


def configurar_oauth(app):

    app.oauth = OAuth(app)

    app.oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        client_kwargs={"scope": "openid email profile"},
    )

    app.oauth.register(
        name="facebook",
        client_id=FACEBOOK_CLIENT_ID,
        client_secret=FACEBOOK_CLIENT_SECRET,
        api_base_url="https://graph.facebook.com/",
        access_token_url="https://graph.facebook.com/v20.0/oauth/access_token",
        authorize_url="https://www.facebook.com/v20.0/dialog/oauth",
        client_kwargs={"scope": "email,public_profile"},
    )

    # === MICROSOFT OPENID CONFIGURATION ADDED HERE ===
    app.oauth.register(
        name="microsoft",
        # Common endpoint for Microsoft/Azure AD V2.0 OpenID Connect
        server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        client_id=MICROSOFT_CLIENT_ID,
        client_secret=MICROSOFT_CLIENT_SECRET,
        client_kwargs={"scope": "openid email profile User.Read"},
        # Authlib defaults to use 'id_token' for user info when using server_metadata_url
    )
    # =================================================

    """
    app.oauth.register(
        name="linkedin",
        client_id=LINKEDIN_CLIENT_ID,
        client_secret=LINKEDIN_CLIENT_SECRET,
        server_metadata_url="https://www.linkedin.com/oauth/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
        client_auth_method="client_secret_post",
        token_endpoint_auth_method="client_secret_post",
    )
    """
