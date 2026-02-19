from flask import current_app, redirect, session, url_for
import logging


logger = logging.getLogger(__name__)


def main():

    db = current_app.db

    logger.info(f"Logout: Id={session.get('id_member')} Correo={session.get('Correo')}")
    session.clear()
    return redirect(url_for("maquinarias"))
