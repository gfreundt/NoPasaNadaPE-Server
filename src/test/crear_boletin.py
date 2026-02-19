from src.comms import generar_mensajes
from jinja2 import Environment, FileSystemLoader
import os
from src.utils.constants import NETWORK_PATH
import uuid


def main(db, idmember, correo):
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-maquinarias-boletin.html")
    cursor = db.cursor()
    subject = ("Alerta de NoPasaNada PE",)
    mensaje = generar_mensajes.redactar_boletin(
        cursor, idmember, template, subject, correo
    )
    path = os.path.join(
        NETWORK_PATH,
        "outbound",
        "temp",
        f"boletin_{uuid.uuid4().hex[:8]}.html",
    )
    with open(path, "w", encoding="utf-8") as file:
        file.write(mensaje["html"])
