from flask import redirect, session, url_for
from src.comms import enviar_correo_inmediato


def main(self):

    cursor = self.db.cursor()

    # copiar registro de miembro a tabla de antiguos, eliminar registro de tabla activa y desasociar placas al id
    cmd = f""" INSERT INTO InfoMiembrosInactivos SELECT * FROM InfoMiembros WHERE IdMember = {session["usuario"]["id_member"]};
               DELETE FROM InfoMiembros WHERE IdMember = {session["usuario"]["id_member"]};
               UPDATE InfoPlacas SET IdMember_FK = 0 WHERE IdMember_FK = {session["usuario"]["id_member"]}
           """
    cursor.executescript(cmd)

    # mandar correo de confirmacion de eliminacion
    enviar_correo_inmediato.eliminacion(
        correo=session["usuario"]["correo"], nombre=session["usuario"]["nombre"]
    )

    # borrar sesion y reenviar a landing
    session.clear()
    return redirect(url_for("maquinarias"))
