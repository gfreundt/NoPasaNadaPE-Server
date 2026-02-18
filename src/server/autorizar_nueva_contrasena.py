from datetime import datetime as dt, timedelta as td
from flask import session, redirect, url_for
import uuid
from src.comms import enviar_correo_inmediato


def main(self):
    """
    crea un token temporal (10 minutos) autorizando al usuario a crear un nuevo password
    envia un correo al usuario con el url unico que incluye el nuevo token
    """

    token = uuid.uuid4().hex
    correo = session["usuario"]["correo"]
    id_member = session["usuario"]["id_member"]

    # ingresa el token a la base de datos
    cursor = self.db.cursor()
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
    self.db.conn.commit()

    # mandar correo
    enviar_correo_inmediato.recuperacion_contrasena(
        self.db,
        correo=correo,
        token=token,
    )

    return redirect(url_for("maquinarias"))
