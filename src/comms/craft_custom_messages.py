import os
from datetime import datetime as dt
from jinja2 import Environment, FileSystemLoader
import uuid
from src.utils.constants import NETWORK_PATH


def craft(db):

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-invitacion01.html")

    messages = []

    # loop all members that required a message
    db.cursor.execute("SELECT IdMember, NombreCompleto, Correo FROM InfoMiembros")
    for member in db.cursor.fetchall():
        messages.append(
            compose_message(
                id_member=member[0],
                nombre=member[1],
                correo=member[2],
                template=template,
                subject="Ayudanos a Seguir Creciendo",
            )
        )

    # save crafted messages as HTML in outbound folder
    for message in messages:
        _file_path = os.path.join(
            NETWORK_PATH, "outbound", f"message_{str(uuid.uuid4())[-6:]}.html"
        )
        with open(_file_path, "w", encoding="utf-8") as file:
            file.write(message)


def compose_message(id_member, nombre, correo, template, subject):

    _info = {
        "nombre": nombre,
        "to": correo,
        "bcc": "gabfre@gmail.com",
        "subject": subject,
    }

    # meta data
    _info.update({"to": correo})
    _info.update({"bcc": "gabfre@gmail.com"})
    _info.update({"subject": subject})
    _info.update({"idMember": id_member})
    _info.update({"timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S")})
    _info.update({"hashcode": "no-hash"})
    _info.update({"attachments": []})
    _info.update({"adjuntos_titulos": ""})

    return template.render(_info)
