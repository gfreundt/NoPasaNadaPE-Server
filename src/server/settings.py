def set_routes(self):

    # user interface routes
    self.app.add_url_rule(
        rule="/",
        endpoint="ui-root",
        view_func=self.login,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/login",
        endpoint="ui-login",
        view_func=self.login,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/recuperar",
        endpoint="ui-recuperar",
        view_func=self.recuperar,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/registro",
        endpoint="ui-registro",
        view_func=self.registro,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/mis-datos",
        endpoint="cuenta-mis-datos",
        view_func=self.mis_datos,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/mis-vencimientos",
        endpoint="cuenta-mis-vencimientos",
        view_func=self.mis_vencimientos,
        methods=["GET", "POST"],
    )
    self.app.add_url_rule(
        rule="/acerca-de",
        endpoint="ui-acerca-de",
        view_func=self.acerca_de,
        methods=["GET"],
    )
    self.app.add_url_rule(
        rule="/logout",
        endpoint="logout",
        view_func=self.logout,
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
        rule="/alta",
        endpoint="alta",
        view_func=self.alta_usuario,
        methods=["POST"],
    )

    # client-routes
    self.app.add_url_rule(
        rule="/maquinarias",
        endpoint="maquinarias",
        view_func=self.maquinarias,
        methods=["GET", "POST"],
    )

    # redirect route (OAuth2)
    self.app.add_url_rule(
        rule="/redir",
        endpoint="backend-redirect-zohomail",
        view_func=self.redir,
        methods=["POST"],
    )


def set_config(self):
    self.app.config["SECRET_KEY"] = "sdlkfjsdlojf3r49tgf8"
    self.app.config["TEMPLATES_AUTO_RELOAD"] = True
