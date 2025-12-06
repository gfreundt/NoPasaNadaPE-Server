from datetime import timedelta as td
from src.utils.constants import (
    FLASK_SECRET_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    FACEBOOK_CLIENT_ID,
    FACEBOOK_CLIENT_SECRET,
    MICROSOFT_CLIENT_ID,
    MICROSOFT_CLIENT_SECRET,
)


def set_routes(self):

    # user interface routes
    self.app.add_url_rule(
        rule="/",
        endpoint="ui-root",
        view_func=self.root,
        methods=["GET", "POST", "HEAD"],
    )

    # rutas maquinarias
    self.app.add_url_rule(
        rule="/maquinarias",
        endpoint="maquinarias",
        view_func=self.maquinarias,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/maquinarias/registro",
        endpoint="maquinarias-registro",
        view_func=self.maquinarias_registro,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/maquinarias/mi-cuenta",
        endpoint="maquinarias-mis-servicios",
        view_func=self.maquinarias_mis_servicios,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/maquinarias/eliminar-cuenta",
        endpoint="maquinarias-eliminar-cuenta",
        view_func=self.maquinarias_eliminar_cuenta,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/maquinarias/mi-perfil",
        endpoint="maquinarias-mi-perfil",
        view_func=self.maquinarias_mi_perfil,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/maquinarias/logout",
        endpoint="maquinarias-logout",
        view_func=self.maquinarias_logout,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/descargar_archivo/<tipo>/<id>",
        view_func=self.descargar_archivo,
        methods=["GET"],
    )
    self.app.add_url_rule(
        rule="/nuevo_password",
        view_func=self.nuevo_password,
        methods=["GET"],
    )

    # self.app.add_url_rule(
    #     rule="/login",
    #     endpoint="ui-login",
    #     view_func=self.login,
    #     methods=["GET", "POST", "HEAD"],
    # )
    # self.app.add_url_rule(
    #     rule="/recuperar",
    #     endpoint="ui-recuperar",
    #     view_func=self.recuperar,
    #     methods=["GET", "POST"],
    # )
    # self.app.add_url_rule(
    #     rule="/registro",
    #     endpoint="ui-registro",
    #     view_func=self.registro,
    #     methods=["GET", "POST"],
    # )
    # self.app.add_url_rule(
    #     rule="/mis-datos",
    #     endpoint="cuenta-mis-datos",
    #     view_func=self.mis_datos,
    #     methods=["GET", "POST"],
    # )
    # self.app.add_url_rule(
    #     rule="/mis-vencimientos",
    #     endpoint="cuenta-mis-vencimientos",
    #     view_func=self.mis_vencimientos,
    #     methods=["GET", "POST"],
    # )
    # self.app.add_url_rule(
    #     rule="/acerca-de",
    #     endpoint="ui-acerca-de",
    #     view_func=self.acerca_de,
    #     methods=["GET"],
    # )
    # self.app.add_url_rule(
    #     rule="/logout",
    #     endpoint="logout",
    #     view_func=self.logout,
    #     methods=["GET"],
    # )

    # direct link
    self.app.add_url_rule(
        rule="/rnt",
        endpoint="rnt",
        view_func=self.rnt,
        methods=["GET"],
    )
    self.app.add_url_rule(
        rule="/terminos-y-condiciones",
        endpoint="terminos-y-condiciones",
        view_func=self.tyc,
        methods=["GET"],
    )
    self.app.add_url_rule(
        rule="/politica-de-privacidad",
        endpoint="politica-de-privacidad",
        view_func=self.pdp,
        methods=["GET"],
    )

    # back end routes
    self.app.add_url_rule(
        rule="/update",
        endpoint="update",
        view_func=self.update,
        methods=["POST"],
    )
    self.app.add_url_rule(
        rule="/api/<version>",
        endpoint="api_version",
        view_func=self.api_externo,
        methods=["POST"],
    )
    self.app.add_url_rule(
        rule="/admin",
        endpoint="admin",
        view_func=self.api_admin,
        methods=["POST"],
    )
    self.app.add_url_rule(
        rule="/google_login",
        endpoint="google_login",
        view_func=self.google_login,
    )
    self.app.add_url_rule(
        rule="/google_callback",
        endpoint="google_authorize",
        view_func=self.google_authorize,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/maq_google_login",
        endpoint="maq_google_login",
        view_func=self.maq_google_login,
    )
    self.app.add_url_rule(
        rule="/maq_google_callback",
        endpoint="maq_google_authorize",
        view_func=self.maq_google_authorize,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/facebook_login",
        endpoint="facebook_login",
        view_func=self.facebook_login,
    )
    self.app.add_url_rule(
        rule="/facebook_callback",
        endpoint="facebook_authorize",
        view_func=self.facebook_authorize,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/instagram_login",
        endpoint="instagram_login",
        view_func=self.instagram_login,
    )
    self.app.add_url_rule(
        rule="/instagram_callback",
        endpoint="instagram_authorize",
        view_func=self.instagram_authorize,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/microsoft_login",
        endpoint="microsoft_login",
        view_func=self.microsoft_login,
    )
    self.app.add_url_rule(
        rule="/microsoft_callback",
        endpoint="microsoft_authorize",
        view_func=self.microsoft_authorize,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/apple_login",
        endpoint="apple_login",
        view_func=self.apple_login,
    )
    self.app.add_url_rule(
        rule="/apple_callback",
        endpoint="apple_authorize",
        view_func=self.apple_authorize,
        methods=["GET", "POST"],
    )


def set_flask_config(self):
    self.app.secret_key = FLASK_SECRET_KEY
    self.app.config["TEMPLATES_AUTO_RELOAD"] = True
    self.app.config["PERMANENT_SESSION_LIFETIME"] = td(minutes=10)
    self.app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_SAMESITE=None,  # <-- Important: allow external redirect from Google
    )
    self.app.config["SESSION_COOKIE_DOMAIN"] = None


def set_oauth_config(self):
    self.oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        client_kwargs={"scope": "openid email profile"},
    )

    self.oauth.register(
        name="facebook",
        client_id=FACEBOOK_CLIENT_ID,
        client_secret=FACEBOOK_CLIENT_SECRET,
        api_base_url="https://graph.facebook.com/",
        access_token_url="https://graph.facebook.com/v20.0/oauth/access_token",
        authorize_url="https://www.facebook.com/v20.0/dialog/oauth",
        client_kwargs={"scope": "email,public_profile"},
    )

    # === MICROSOFT OPENID CONFIGURATION ADDED HERE ===
    self.oauth.register(
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
    self.oauth.register(
        name="linkedin",
        client_id=LINKEDIN_CLIENT_ID,
        client_secret=LINKEDIN_CLIENT_SECRET,
        server_metadata_url="https://www.linkedin.com/oauth/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
        client_auth_method="client_secret_post",
        token_endpoint_auth_method="client_secret_post",
    )
    """
