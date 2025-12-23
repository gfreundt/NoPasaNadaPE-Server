import os
from datetime import datetime as dt
import json
from src.utils.email import Email
from src.utils.constants import NETWORK_PATH
from security.keys import ZEPTOMAIL_INFO_TOKEN


def send(db):

    cursor = db.cursor()
    conn = db.conn

    # activate send account
    email = Email(
        cursor=cursor,
        conn=conn,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # procesar contenido de cada archivo de pendientes por separado
    respuesta = []
    for pendiente in ("boletines_pendientes.json", "alertas_pendientes.json"):

        if "boletines" in pendiente:
            tipo_mensaje = "BOLETIN"
        elif "alertas" in pendiente:
            tipo_mensaje = "ALERTA"

        # extraer listado de mensajes de un archivo de pendientes
        with open(
            mode="r", file=os.path.join(NETWORK_PATH, "outbound", pendiente)
        ) as file:
            data = json.load(file)

        # iterar sobre todos los mensajes pendientes dentro del archivo
        rpta = []
        for mensaje in data:

            # transformar data de mensaje pendiente a formato esperado
            formato_zeptomail = {
                "id_member": mensaje["idMember"],
                "tipo_mensaje": tipo_mensaje,
                "fecha_creacion": mensaje["timestamp"],
                "to_address": mensaje["to"],
                "bcc": mensaje["bcc"],
                "subject": mensaje["subject"],
                "hashcode": mensaje["hashcode"],
                "html_content": mensaje["html"],
                "reset_next_send": mensaje["reset_next_send"],
            }

            # armar correos en bulk
            resp_zeptomail = email.send_zeptomail(formato_zeptomail, simulation=False)
            rpta.append(1 if resp_zeptomail else 0)

            # actualiza base de datos indicando que siguiente mensaje es en un mes
            cmd = "UPDATE InfoMiembros SET NextMessageSend = DATE('now', '+1 month') WHERE IdMember = ?"
            cursor.execute(
                cmd,
                (mensaje["idMember"],),
            )
        conn.commit()

        # proceso solo si hubieron mensajes que enviar
        if data:

            # cambiar nombre de archivo de "pendientes" a "enviados" y agregar fecha
            nuevo_nombre = pendiente.replace(
                "pendientes", f"enviados-{dt.strftime(dt.now(),"%Y-%m-%d %H:%M:%S")}"
            )
            os.rename(
                os.path.join(NETWORK_PATH, "outbound", pendiente),
                os.path.join(NETWORK_PATH, "outbound", nuevo_nombre),
            )

        # cuenta de boletines y alertas enviadas (en ese orden)
        respuesta.append(len(data))

    return respuesta
