import os
import uuid
import json
from datetime import datetime as dt
from jinja2 import Environment, FileSystemLoader

from src.comms import redactar_mensaje
from src.utils.constants import NETWORK_PATH
from src.utils.utils import date_to_mail_format
from src.maintenance import maintenance
from src.updates import datos_actualizar, necesitan_mensajes


def alertas(cursor):
    """
    Crea el HTML de las alertas que deben ser enviadas en esta iteración y
    las guarda en el folder "outbound".
    """

    # Load HTML template
    environment = Environment(loader=FileSystemLoader("templates/"))
    template_alertas = environment.get_template("comms-maquinarias-alerta.html")

    alertas = []
    for row in necesitan_mensajes.alertas(cursor):
        mensaje = redactar_mensaje.alerta(
            db_cursor=cursor,
            idmember=row["IdMember"],
            template=template_alertas,
            subject="Alerta de No Pasa Nada PE",
            tipo_alerta=row["TipoAlerta"],
            vencido=bool(row["Vencido"]),
            fecha_hasta=row["FechaHasta"],
            placa=row["Placa"],
            doc_tipo=row["DocTipo"],
            doc_num=row["DocNum"],
        )
        if not mensaje:
            continue
        else:
            alertas.append(mensaje)

    # Guardar los mensajes en la carpeta outbound
    maintenance.clear_outbound_folder("alerta")
    # guardar data en archivo (reemplaza al anterior)
    path = os.path.join(NETWORK_PATH, "outbound", "alertas_pendientes.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(alertas, file, indent=4)

    return [i["html"] for i in alertas]


def boletines(db_cursor):
    """
    Crea mensajes regulares en HTML y los guarda en /outbound.
    """

    # Carga plantilla HTML
    environment = Environment(loader=FileSystemLoader("templates/"))
    template_regular = environment.get_template("comms-maquinarias-boletin.html")

    boletines = []
    for row in necesitan_mensajes.boletines(db_cursor):
        boletines.append(
            obtener_datos_boletin(
                db_cursor=db_cursor,
                IdMember=row["IdMember"],
                template=template_regular,
                subject="Tu Boletín de No Pasa Nada PE - Diciembre 2025",
                alertas=alertas,
                correo=row["Correo"],
            )
        )

    # Guardar los mensajes en la carpeta outbound
    maintenance.clear_outbound_folder("boletin")
    # guardar data en archivo (reemplaza al anterior)
    path = os.path.join(NETWORK_PATH, "outbound", "boletines_pendientes.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(boletines, file, indent=4)

    return [i["html"] for i in boletines]


def obtener_datos_boletin(db_cursor, IdMember, template, subject, alertas, correo):
    """
    Arma toda la información necesaria para un mensaje HTML individual.
    """

    # Información del miembro
    db_cursor.execute("SELECT * FROM InfoMiembros WHERE IdMember = ?", (IdMember,))
    member = db_cursor.fetchone()
    if not member:
        return ""  # evita crasheos si el IdMember está huérfano

    # Placas asociadas
    db_cursor.execute("SELECT Placa FROM InfoPlacas WHERE IdMember_FK = ?", (IdMember,))
    placas = [row["Placa"] for row in db_cursor.fetchall()]

    # Generar hash único para email tracking
    email_id = f"{member['CodMemberInterno']}|{str(uuid.uuid4())[-12:]}"

    # Crear HTML final usando tu mega función compose()
    return redactar_mensaje.boletin(
        db_cursor=db_cursor,
        member=member,
        template=template,
        email_id=email_id,
        subject=subject,
        alertas=alertas,
        placas=placas,
        correo=correo,
    )
