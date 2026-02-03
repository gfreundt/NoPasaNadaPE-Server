import os
import uuid
import json
from datetime import datetime as dt
from jinja2 import Environment, FileSystemLoader


from src.utils.constants import NETWORK_PATH, MESES_NOMBRE_COMPLETO
from src.updates.datos_actualizar import (
    get_alertas_para_mensajes,
    get_boletines_para_mensajes,
    get_alertas_para_actualizar,
)
from src.utils.utils import date_to_mail_format
from src.ui.maquinarias.servicios import generar_data_servicios


def alertas(self):
    """
    Crea el HTML de las alertas que deben ser enviadas en esta iteración y
    las guarda en el folder "outbound".
    """

    cursor = self.db.cursor()

    # Load HTML template
    environment = Environment(loader=FileSystemLoader("templates/"))
    template_alertas = environment.get_template("comms-maquinarias-alerta.html")

    alertas = []

    for row in get_alertas_para_mensajes(self):
        mensaje = redactar_alerta(
            db_cursor=cursor,
            idmember=row["IdMember"],
            template=template_alertas,
            subject="Alerta de NoPasaNada PE",
            tipo_alerta=row["Categoria"],
            vencido=(
                True if dt.strptime(row["FechaHasta"], "%Y-%M-%d") < dt.now() else False
            ),
            fecha_hasta=row["FechaHasta"],
            placa=row["Placa"],
            doc_tipo=row["DocTipo"],
            doc_num=row["DocNum"],
        )

        if not mensaje:
            continue
        else:
            alertas.append(mensaje)

    # guardar data en archivo en outbound (reemplaza al anterior)
    path = os.path.join(NETWORK_PATH, "outbound", "alertas_pendientes.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(alertas, file, indent=4)

    return len(alertas)


def redactar_alerta(
    db_cursor,
    idmember,
    template,
    subject,
    tipo_alerta,
    vencido,
    fecha_hasta,
    placa,
    doc_tipo,
    doc_num,
):
    """Construye el HTML final usando la plantilla Jinja2."""

    # Secure SELECT
    db_cursor.execute(
        "SELECT NombreCompleto, Correo, IdMember, CodMemberInterno FROM InfoMiembros WHERE IdMember = ? LIMIT 1",
        (idmember,),
    )
    member = db_cursor.fetchone()

    if not member:
        return None

    # Random hash for tracking
    email_id = f"{member['CodMemberInterno']}|{uuid.uuid4().hex[-12:]}"

    if tipo_alerta == "DataMtcBrevetes":
        servicio = "Licencia de Conducir"
        genero = "O"

    elif tipo_alerta == "DataMtcRevisionesTecnicas":
        servicio = "Revisión Técnica"
        genero = "A"

    elif tipo_alerta == "DataApesegSoats":
        servicio = "Certificado SOAT"
        genero = "O"

    elif (
        tipo_alerta
        == "DataSatImpuestosCodigos a JOIN DataSatImpuestosDeudas b ON a.Codigo = b.Codigo"
    ):
        servicio = "Impuesto Vehicular SAT Lima"
        genero = "O"

    # Build final data injection dict
    info = {
        "nombre_usuario": member["NombreCompleto"],
        "fecha_hasta": date_to_mail_format(fecha_hasta),
        "genero": genero,
        "servicio": servicio,
        "placa": placa,
        "vencido": vencido,
        "ano": dt.strftime(dt.now(), "%Y"),
    }

    return {
        "to": member["Correo"],
        "bcc": "gabfre@gmail.com",
        "subject": subject,
        "idMember": int(member["IdMember"]),
        "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hashcode": email_id,
        "attachment_paths": [],
        "reset_next_send": 0,
        "html": template.render(info),
    }


def boletines(self):
    """
    Crea mensajes regulares en HTML y los guarda en /outbound.
    """

    cursor = self.db.cursor()

    # Carga plantilla HTML
    environment = Environment(loader=FileSystemLoader("templates/"))
    template_regular = environment.get_template("comms-maquinarias-boletin.html")

    mes = MESES_NOMBRE_COMPLETO[int(dt.strftime(dt.now(), "%m")) - 1]

    boletines = []
    for row in get_boletines_para_mensajes(self):
        mensaje = redactar_boletin(
            cursor,
            IdMember=row["IdMember"],
            template=template_regular,
            subject=f"Tu Boletín de No Pasa Nada PE - {mes} 2025",
            correo=row["Correo"],
        )

        if not mensaje:
            continue
        else:
            boletines.append(mensaje)

    # guardar data en archivo (reemplaza al anterior)
    path = os.path.join(NETWORK_PATH, "outbound", "boletines_pendientes.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(boletines, file, indent=4)

    return len(boletines)


def redactar_boletin(cursor, IdMember, template, subject, correo):
    """
    Arma toda la información necesaria para un mensaje HTML individual.
    """

    data_servicios = generar_data_servicios(cursor, correo)

    return {
        "to": correo,
        "bcc": "gabfre@gmail.com",
        "subject": subject,
        "idMember": int(IdMember),
        "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hashcode": f"{str(uuid.uuid4())[-12:]}",
        "attachment_paths": [],
        "reset_next_send": 0,
        "html": template.render(data_servicios),
    }
