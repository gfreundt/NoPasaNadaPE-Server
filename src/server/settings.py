from datetime import timedelta as td
from security.keys import (
    FLASK_SECRET_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    FACEBOOK_CLIENT_ID,
    FACEBOOK_CLIENT_SECRET,
    MICROSOFT_CLIENT_ID,
    MICROSOFT_CLIENT_SECRET,
    DASHBOARD_URL,
)


def set_server_routes(self):

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
        rule="/maquinarias/terminos-y-condiciones",
        endpoint="maquinarias-tyc",
        view_func=self.maquinarias_tyc,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/maquinarias/politica-de-privacidad",
        endpoint="maquinarias-pdp",
        view_func=self.maquinarias_pdp,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/maquinarias/documentacion-api-v1",
        endpoint="documentacion-api-v1",
        view_func=self.documentacion_api_v1,
        methods=["GET"],
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
        rule="/recuperar-contrasena/<token>",
        endpoint="recuperar_contrasena",
        view_func=self.recuperar_contrasena,
        methods=["GET", "POST"],
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
    # --- DASHBOARD


def set_dash_routes(self):
    # -------- URL DE INGRESO --------
    self.app.add_url_rule(
        f"/{DASHBOARD_URL}",
        endpoint="dashboard",
        view_func=self.dash.dashboard,
    )
    # endpoint usado por JavaScript para actualizar datos (AJAX)
    self.app.add_url_rule(
        "/data",
        "get_data",
        self.dash.get_data,
    )
    # -------- BOTONES --------
    self.app.add_url_rule(
        "/datos_alertas",
        endpoint="datos_alerta",
        view_func=self.dash.datos_alerta,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/datos_boletines",
        endpoint="datos_boletin",
        view_func=self.dash.datos_boletin,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/actualizar_alertas",
        endpoint="actualizar_alertas",
        view_func=self.dash.actualizar_alertas,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/actualizar_boletines",
        endpoint="actualizar_boletines",
        view_func=self.dash.actualizar_boletines,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/generar_alertas",
        endpoint="generar_alertas",
        view_func=self.dash.generar_alertas,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/enviar_mensajes",
        endpoint="enviar_mensajes",
        view_func=self.dash.enviar_mensajes,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/generar_boletines",
        endpoint="generar_boletines",
        view_func=self.dash.generar_boletines,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/test",
        endpoint="test",
        view_func=self.dash.hacer_tests,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/logs",
        endpoint="logs",
        view_func=self.dash.actualizar_logs,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/db_info",
        endpoint="db_info",
        view_func=self.dash.db_info,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/db_backup",
        endpoint="db_backup",
        view_func=self.dash.db_completa,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/actualizar_de_json",
        endpoint="actualizar_de_json",
        view_func=self.dash.actualizar_de_json,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/clear_logs",
        "clear_logs",
        self.dash.clear_logs,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/db_vacuum",
        "db_vacuum",
        self.dash.db_vacuum,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/toggle_scraper_status",
        "toggle_scraper_status",
        self.dash.toggle_scraper_status,
        methods=["POST"],
    )
    self.app.add_url_rule(
        "/toggle_config",
        "toggle_config",
        self.dash.toggle_config,
        methods=["POST"],
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
