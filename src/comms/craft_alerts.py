import os
from jinja2 import Environment, FileSystemLoader
from datetime import datetime as dt
import uuid
from src.utils.constants import NETWORK_PATH
from src.utils.utils import date_to_mail_format


def craft(db_cursor):
    """crea el HTML de las alertas que deben ser enviadas en esta iteracion y las guarda en el folder "outbound" """

    # carga plantilla HTML
    environment = Environment(loader=FileSystemLoader("templates/"))
    template_alertas = environment.get_template("comms-alerta.html")

    # definir el codigo de la alerta
    alerts = []
    index_alertas = {
        "SOAT": 1,
        "REVTEC": 3,
        "SATIMP": 5,
        "BREVETE": 7,
        "DNI": 9,
        "PASAPORTE/VISA": 11,
    }

    # iterar por todos los miembros que necesitan una alerta y componer el mensaje
    db_cursor.execute(
        "SELECT IdMember_FK, TipoAlerta, Vencido, FechaHasta, Placa, DocTipo FROM _necesitan_alertas"
    )
    for (
        idmember,
        tipo_alerta,
        vencido,
        fecha_hasta,
        placa,
        doc_tipo,
    ) in db_cursor.fetchall():

        if idmember:
            alerts.append(
                compose_message(
                    db_cursor,
                    idmember=idmember,
                    template=template_alertas,
                    fecha_hasta=fecha_hasta,
                    subject="ALERTA de No Pasa Nada PE",
                    msg_type=index_alertas[tipo_alerta],
                    tipo_alerta=tipo_alerta,
                    vencido=vencido,
                    placa=placa,
                    doc_tipo=doc_tipo,
                )
            )

    # grabar las alertas en folder "outbound" en preparacion para ser enviados por correo
    for k, alert in enumerate(alerts):
        if alert:
            # write in outbound folder
            with open(
                os.path.join(NETWORK_PATH, "outbound", f"alert_{k:03d}.html"),
                "w",
                encoding="utf-8",
            ) as file:
                file.write(alert)


def compose_message(
    db_cursor,
    idmember,
    template,
    subject,
    msg_type,
    tipo_alerta,
    vencido,
    fecha_hasta,
    placa,
    doc_tipo,
):
    """recibe la data del mensaje y genera en HTML llenando las variables con los datos recibidos y la plantilla"""

    # extraer detalles del miembro de la base de datos
    db_cursor.execute(f"SELECT * FROM InfoMiembros WHERE IdMember = {idmember}")
    member = db_cursor.fetchone()

    if not member:
        return

    # generate random email hash
    email_id = f"{member['CodMember']}|{str(uuid.uuid4())[-12:]}"

    # variable que contiene toda la informacion que recibira la plantilla HTML
    _info = {}

    # determinar que vence para elegir el texto correspondiente
    titulo_alerta = "⚠️ Alerta de Vencimiento"
    if tipo_alerta == "BREVETE":
        _t = "Licencia de Conducir"
    elif tipo_alerta == "REVTEC":
        _t = f"Revisión Técnica para placa {placa}"
    elif tipo_alerta == "SOAT":
        _t = f"SOAT para placa {placa}"
    elif tipo_alerta == "SATIMP":
        _t = "Impuesto Vehicular SAT Lima"
    elif tipo_alerta == "DNI":
        _t = "Documento Nacional de Identidad"
    elif tipo_alerta == "PASAPORTE/VISA":
        _t = f"Pasaporte/Visa de {doc_tipo}"

    # armado de la informacion que recibira la plantilla
    _texto_alerta = f"Tu {_t} {"ha vencido" if vencido else "está cerca de vencer"} el {date_to_mail_format(fecha_hasta)}."
    _info.update(
        {
            "nombre_usuario": member["NombreCompleto"],
            "codigo_correo": email_id,
            "titulo_alerta": titulo_alerta,
            "texto_alerta": _texto_alerta,
            "vencido": vencido,
        }
    )

    # meta data usada para el envio del correo y guardado del mensaje enviado en la base de datos
    _info.update({"to": member["Correo"]})
    _info.update({"bcc": "gabfre@gmail.com"})
    _info.update({"subject": f"{subject}"})
    _info.update({"msg_types": [msg_type]})
    _info.update({"idMember": int(member["IdMember"])})
    _info.update({"timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S")})
    _info.update({"hashcode": f"{member[1]}|{str(uuid.uuid4())[-12:]}"})
    _info.update({"attachment_paths": []})
    _info.update({"reset_next_send": 0})

    return template.render(_info)
