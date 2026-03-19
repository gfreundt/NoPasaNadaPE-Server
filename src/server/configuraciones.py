from datetime import timedelta as td
from flask import render_template
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from authlib.integrations.flask_client import OAuth

from security.keys import (
    FLASK_SECRET_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    FACEBOOK_CLIENT_ID,
    FACEBOOK_CLIENT_SECRET,
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

from src.scrapers import (
    scrape_brevete,
    scrape_revtec,
    scrape_sutran,
    scrape_satimp,
    scrape_recvehic,
    scrape_sunarp,
    scrape_satmul,
    scrape_soat,
    scrape_calmul,
    scrape_maqmant,
    scrape_sbs_seguro,
)


def definir_rutas(app):
    """
    Define las rutas de la aplicacion:
        - Landing: punto de entrada.
        - Rutas UI (dinamicas): requieren procesamiento de backend (manejo de formularios, etc.)
        - Rutas UI (texto fijo): solo muestran contenido estatico, sin necesidad de procesamiento en backend.
        - Rutas de APIs
        - Rutas para login de terceros (OAuth).
    """

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
        endpoint="maquinarias-login",
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
        view_func=api_externo.version_select,
        methods=["POST"],
    )
    app.add_url_rule(
        rule="/admin",
        endpoint="admin",
        view_func=api_admin.main,
        methods=["POST"],
    )

    # Login de terceros
    # ACTIVOS: Google, Facebook
    # PENDIENTES: Microsoft, Instagram, Apple
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
    """
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
    """


def configurar_flask(app):
    """
    Configura la aplicacion de Flask, definiendo:
        - Clave secreta para sesiones.
        - Configuraciones de seguridad para cookies.
        - Manejo de errores HTTP y excepciones no manejadas.
    """
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    app.jinja_env.add_extension("jinja2.ext.do")
    app.secret_key = FLASK_SECRET_KEY
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = td(minutes=10)
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE="None",
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
    """
    Configura OAuth para login de terceros, definiendo:
        ACTIVOS:
            - Google
            - Facebook
        PENDIENTES:
            - Microsoft
            - Instagram
            - Apple
    """

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

    """
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


def parametros_scrapers(app):

    app.parametros_scrapers = {
        "DataMtcRecordsConductores": {
            "activo": True,
            "api": False,
            "residential_proxy": False,
            "indice_placa": False,
            "funcion_scraper": scrape_recvehic,
            "timeout": 90,
            "estructura_respuesta": {
                "ImageBytes": 0,
            },
            "campo_fecha_hasta": "",
            "genera_alerta": False,
        },
        "DataMtcBrevetes": {
            "activo": True,
            "api": False,
            "residential_proxy": True,
            "indice_placa": False,
            "funcion_scraper": scrape_brevete,
            "timeout": 90,
            "estructura_respuesta": {
                "Clase": 0,
                "Numero": 1,
                "Tipo": 2,
                "FechaExp": 3,
                "Restricciones": 4,
                "FechaHasta": 5,
                "Centro": 6,
                "Puntos": 7,
                "Record": 8,
            },
            "campo_fecha_hasta": "FechaHasta",
            "alerta_dias": [-45, -25, -5, 0, 1, 2, 3],
            "genera_alerta": True,
        },
        "DataSatMultas": {
            "activo": True,
            "api": False,
            "residential_proxy": False,
            "indice_placa": True,
            "funcion_scraper": scrape_satmul,
            "timeout": 300,
            "estructura_respuesta": {
                "IdPlaca_FK": None,
                "PlacaValidate": 0,
                "Reglamento": 1,
                "Falta": 2,
                "Documento": 3,
                "FechaEmision": 4,
                "Importe": 5,
                "Gastos": 6,
                "Descuento": 7,
                "Deuda": 8,
                "Estado": 9,
                "Licencia": 10,
                "DocTipoSatmul": 11,
                "DocNumSatmul": 12,
                "ImageBytes1": 13,
                "ImageBytes2": 14,
            },
            "campo_fecha_hasta": "",
            "genera_alerta": False,
        },
        "DataSatImpuestos": {
            "activo": True,
            "api": False,
            "residential_proxy": False,
            "indice_placa": False,
            "funcion_scraper": scrape_satimp,
            "timeout": 90,
            "estructura_respuesta": {
                "Codigo": 0,
                "Ano": 1,
                "Periodo": 2,
                "DocNum": 3,
                "TotalAPagar": 4,
                "FechaHasta": 5,
            },
            "campo_fecha_hasta": "FechaHasta",
            "alerta_dias": [-10, -5, -1, 0, 1, 2, 3],
            "genera_alerta": True,
        },
        "DataMtcRevisionesTecnicas": {
            "activo": True,
            "api": False,
            "residential_proxy": True,
            "indice_placa": True,
            "funcion_scraper": scrape_revtec,
            "timeout": 90,
            "estructura_respuesta": {
                "IdPlaca_FK": None,
                "Certificadora": 0,
                "PlacaValidate": 2,
                "Certificado": 3,
                "FechaDesde": 4,
                "FechaHasta": 5,
                "Resultado": 6,
                "Vigencia": 7,
                "FechaHastaFueCalculada": 8,
            },
            "campo_fecha_hasta": "FechaHasta",
            "alerta_dias": [-25, -15, -5, 0, 1, 2, 3],
            "genera_alerta": True,
        },
        "DataSutranMultas": {
            "activo": True,
            "api": False,
            "residential_proxy": False,
            "indice_placa": True,
            "funcion_scraper": scrape_sutran,
            "timeout": 90,
            "estructura_respuesta": {
                "Documento": 0,
                "Tipo": 1,
                "FechaDoc": 2,
                "CodigoInfrac": 3,
                "Clasificacion": 4,
            },
            "campo_fecha_hasta": "",
            "genera_alerta": False,
        },
        "DataSunarpFichas": {
            "activo": False,
            "api": False,
            "residential_proxy": True,
            "indice_placa": True,
            "funcion_scraper": scrape_sunarp,
            "timeout": 90,
            "genera_alerta": False,
            "campo_fecha_hasta": None,
        },
        "DataApesegSoats": {
            "activo": True,
            "api": False,
            "residential_proxy": False,
            "indice_placa": True,
            "funcion_scraper": scrape_soat,
            "timeout": 90,
            "estructura_respuesta": {
                "IdPlaca_FK": None,
                "Aseguradora": 0,
                "Vigencia": 1,
                "FechaInicio": 2,
                "FechaHasta": 3,
                "PlacaValidate": 4,
                "Certificado": 5,
                "Uso": 6,
                "Clase": 7,
                "Tipo": 8,
                "FechaVenta": 9,
                "ImageBytes": 12,
            },
            "campo_fecha_hasta": "FechaHasta",
            "alerta_dias": [-10, -5, -1, 0, 1, 2, 3],
            "genera_alerta": True,
        },
        "DataCallaoMultas": {
            "activo": True,
            "api": False,
            "residential_proxy": False,
            "indice_placa": True,
            "funcion_scraper": scrape_calmul,
            "timeout": 60,
            "estructura_respuesta": {
                "PlacaValidate": 0,
                "Codigo": 1,
                "NumeroPapeleta": 2,
                "FechaInfraccion": 3,
                "TotalInfraccion": 4,
                "TotalBeneficio": 5,
                "ImageBytes": None,
            },
            "campo_fecha_hasta": "",
            "genera_alerta": False,
        },
        "DataMaquinariasMantenimiento": {
            "activo": True,
            "api": True,
            "residential_proxy": False,
            "indice_placa": True,
            "funcion_scraper": scrape_maqmant,
            "timeout": 20,
            "estructura_respuesta": {
                "FechaUltimoServicio": 0,
                "UltimoServicioDetalle": 1,
                "FechaProximoServicio": 2,
                "ProximoServicioDetalle": 3,
                "PlacaValidate": 4,
                "IdPlaca_FK": None,
            },
            "campo_fecha_hasta": "FechaProximoServicio",
            "alerta_dias": [-10, -5, -1, 0, 1, 2, 3],
            "genera_alerta": True,
        },
        "DataSbsSegurosVehiculares": {
            "activo": True,
            "api": False,
            "residential_proxy": False,
            "indice_placa": True,
            "funcion_scraper": scrape_sbs_seguro,
            "timeout": 90,
            "estructura_respuesta": {
                "CompaniaAseguradora": 0,
                "ClaseVehiculo": 1,
                "UsoVehiculo": 2,
                "Accidentes": 3,
                "NumeroPoliza": 4,
                "NumeroCertificado": 5,
                "FechaInicio": 6,
                "FechaHasta": 7,
                "Comentario": 8,
            },
            "campo_fecha_hasta": "",
            "alerta_dias": [-10, -5, -1, 0, 1, 2, 3],
            "genera_alerta": True,
        },
    }
