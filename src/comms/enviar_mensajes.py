import os
from datetime import datetime as dt
import json
import logging

from src.utils.email import Email
from src.utils.constants import NETWORK_PATH
from security.keys import ZEPTOMAIL_INFO_TOKEN


logger = logging.getLogger(__name__)


def main(self, tipo_mensaje, simulation=False):

    cursor = self.db.cursor()
    conn = self.db.conn

    # activate send account
    email = Email(
        cursor=cursor,
        conn=conn,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # extraer listado de mensajes de un archivo de pendientes
    archivo = os.path.join(NETWORK_PATH, "outbound", f"{tipo_mensaje}_pendientes.json")
    if os.path.exists(archivo):
        with open(mode="r", file=archivo) as file:
            data = json.load(file)
    else:
        logger.info(f"No existe archivo {archivo}.")
        return True

    # iterar sobre todos los mensajes pendientes dentro del archivo
    respuesta = []
    for mensaje in data:
        # transformar data de mensaje pendiente a formato esperado
        formato_zeptomail = {
            "id_member": mensaje["idMember"],
            "tipo_mensaje": "ALERTA" if tipo_mensaje == "alertas" else "BOLETIN",
            "fecha_creacion": mensaje["timestamp"],
            "to_address": mensaje["to"],
            "bcc": mensaje["bcc"],
            "subject": mensaje["subject"],
            "hashcode": mensaje["hashcode"],
            "html_content": mensaje["html"],
            # "reset_next_send": mensaje["reset_next_send"],
        }

        # armar correos en bulk
        logger.info(
            f"Solicitud enviar correo a {mensaje['to']}. Subject: {mensaje['subject']}"
        )
        respuesta.append(email.send_zeptomail(formato_zeptomail, simulation=simulation))

        if simulation:
            mensaje["reset_next_send"] = False

        # actualiza base de datos indicando que siguiente mensaje es en un mes
        if mensaje["reset_next_send"]:
            cmd = "UPDATE InfoMiembros SET NextMessageSend = DATE('now', 'localtime', '+30 days') WHERE IdMember = ?"
            cursor.execute(
                cmd,
                (mensaje["idMember"],),
            )

    conn.commit()

    # proceso solo si hubieron mensajes que enviar
    if data:
        # cambiar nombre de archivo de "pendientes" a "enviados" y agregar fecha
        nuevo_archivo = archivo.replace(
            "pendientes", f"enviados-{dt.strftime(dt.now(), '%Y-%m-%d %H:%M:%S')}"
        )
        os.rename(
            os.path.join(NETWORK_PATH, "outbound", archivo),
            os.path.join(NETWORK_PATH, "outbound", nuevo_archivo),
        )

    # retornar True si todos los mensajes enviados correctamente, False cualquier otra cosa
    return all(respuesta)
