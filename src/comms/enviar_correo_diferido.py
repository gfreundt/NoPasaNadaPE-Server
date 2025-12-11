import os
from datetime import datetime as dt, timedelta as td
import json
from src.utils.email import Email
from src.utils.constants import NETWORK_PATH
from security.keys import ZEPTOMAIL_INFO_TOKEN


def send(cursor, conn):

    # activate send account
    email = Email(
        cursor=cursor,
        conn=conn,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # elegir los archivos con la palabra "pendientes" y "json" en el nombre en /outbound
    pendientes = [
        i
        for i in os.listdir(os.path.join(NETWORK_PATH, "outbound"))
        if "pendientes" in i and ".json" in i
    ]

    # procesar contenido de cada archivo de pendientes por separado
    respuesta = []
    for pendiente in pendientes:

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
            cmd = "UPDATE InfoMiembros SET NextMessageSend = DATE(NextMessageSend, '+1 month') WHERE Correo = ?"
            cursor.execute(
                cmd,
                (mensaje["to"]),
            )

        respuesta.append(f"{pendiente} - {sum(rpta)} Correctos de {len(data)}")
        conn.commit()

    # erase message from outbound folder
    # os.remove(os.path.join(NETWORK_PATH, "outbound", html_file))

    return respuesta
