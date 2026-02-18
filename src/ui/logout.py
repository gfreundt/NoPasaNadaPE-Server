from flask import redirect, url_for
import logging

logger = logging.getLogger(__name__)


def main(self):

    # If user is logged in → log the logout event
    if self.session.get("loaded_user"):
        user = self.session["loaded_user"]
        logger.info(
            f"Logout: {user['CodMember']} | {user['NombreCompleto']} | {user['DocNum']} | {user['Correo']}"
        )

    # Clear session
    self.session.clear()

    # Redirect to login page
    return redirect(url_for("ui-login"))
