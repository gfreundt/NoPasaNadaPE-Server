from flask import redirect, session, url_for
from src.comms import enviar_correo_inmediato


def main(self):

    cursor = self.db.cursor()
    id_member = session["usuario"]["id_member"]
    correo = session["usuario"]["correo"]
    nombre = session["usuario"]["nombre"]

    # copiar registro de miembro a tabla de antiguos, eliminar registro de tabla activa y desasociar placas al id
    cmd = """ INSERT INTO InfoMiembrosInactivos SELECT * FROM InfoMiembros WHERE IdMember = ?;
              DELETE FROM InfoMiembros WHERE WHERE IdMember = ?;
              UPDATE InfoPlacas SET IdMember_FK = 0 WHERE IdMember_FK = ?"
            """
    cursor.executescript(cmd, (id_member, id_member, id_member))

    # mandar correo de confirmacion de eliminacion
    enviar_correo_inmediato.eliminacion(correo=correo, nombre=nombre)

    # borrar sesion y reenviar a landing
    session.clear()
    return redirect(url_for("maquinarias"))
