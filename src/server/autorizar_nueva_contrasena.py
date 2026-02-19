from datetime import datetime as dt, timedelta as td
from flask import current_app, session, redirect, url_for
import uuid
import logging

from src.comms import enviar_correo_inmediato


logger = logging.getLogger(__name__)


def main():
    """
    crea un token temporal (10 minutos) autorizando al usuario a crear un nuevo password
    envia un correo al usuario con el url unico que incluye el nuevo token
    """

    db = current_app.db

    token = uuid.uuid4().hex
    correo = session["usuario"]["correo"]
    id_member = session["usuario"]["id_member"]

    # ingresa el token a la base de datos
    cursor = db.cursor()
    cmd = """
                    INSERT INTO StatusTokens 
                    (IdMember, TokenHash, TokenTipo, Correo, FechaHasta, TokenUsado)
                    VALUES 
                    (?, ?, ?, ?, ?, ?)
                """
    cursor.execute(
        cmd,
        (
            id_member,
            token,
            "Password",
            correo,
            dt.now() + td(minutes=10),
            0,
        ),
    )
    db.conn.commit()
    logger.info(
        f"Token de Recuperacion de Password para {correo} Creado: {token[:5]}...{token[-5:]}"
    )

    # mandar correo
    enviar_correo_inmediato.recuperacion_contrasena(
        db,
        correo=correo,
        token=token,
    )

    return redirect(url_for("maquinarias"))
