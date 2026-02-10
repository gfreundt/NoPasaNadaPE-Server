import os
import uuid
import json
from datetime import datetime as dt
from jinja2 import Environment, FileSystemLoader


from src.utils.constants import NETWORK_PATH, MESES_NOMBRE_COMPLETO

from src.updates.datos_actualizar import get_datos_alertas, get_datos_boletines
from src.utils.utils import date_to_mail_format
from src.ui.maquinarias.servicios import generar_data_servicios

import logging

logger = logging.getLogger(__name__)


def alertas(self):
    """
    Crea el HTML de las alertas que deben ser enviadas en esta iteración y
    las guarda en el folder "outbound".
    """
    try:
        cursor = self.db.cursor()

        # Load HTML template
        environment = Environment(loader=FileSystemLoader("templates/"))
        template_alertas = environment.get_template("comms-maquinarias-alerta.html")

        alertas = []

        for row in get_datos_alertas(self, premensaje=False):
            mensaje = redactar_alerta(
                cursor=cursor,
                idmember=row["IdMember"],
                template=template_alertas,
                subject="Alerta de NoPasaNada PE",
                tipo_alerta=row["Categoria"],
                vencido=(
                    True
                    if dt.strptime(row["FechaHasta"], "%Y-%M-%d") < dt.now()
                    else False
                ),
                fecha_hasta=row["FechaHasta"],
                placa=row["Placa"],
                doc_tipo=row["DocTipo"],
                doc_num=row["DocNum"],
            )

            if not mensaje:
                continue
            else:
                logger.info(
                    f"Alerta (IdMember = {row['IdMember']}) generada correctamente."
                )
                logger.debug(f"Alerta generada: {mensaje}")
                alertas.append(mensaje)

                # solo para ver html
                path = os.path.join(
                    NETWORK_PATH,
                    "outbound",
                    "temp",
                    f"alerta_{uuid.uuid4().hex[:8]}.html",
                )
                with open(path, "w", encoding="utf-8") as file:
                    file.write(mensaje["html"])

        # guardar data en archivo en outbound (reemplaza al anterior)
        if alertas:
            path = os.path.join(NETWORK_PATH, "outbound", "alertas_pendientes.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump(alertas, file, indent=4)
            logger.info(
                f"Archivo 'alertas_pendientes.json' grabado correctamente. Total alertas = {len(alertas)}"
            )

        return True

    except Exception as e:
        logger.warning(f"Error generando alertas: {e}")
        return False


def redactar_alerta(
    cursor,
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
    cursor.execute(
        "SELECT NombreCompleto, Correo, IdMember, CodMemberInterno FROM InfoMiembros WHERE IdMember = ? LIMIT 1",
        (idmember,),
    )
    member = cursor.fetchone()

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

    elif tipo_alerta == "DataSatImpuestos":
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

    try:
        cursor = self.db.cursor()

        # Carga plantilla HTML
        environment = Environment(loader=FileSystemLoader("templates/"))
        template_regular = environment.get_template("comms-maquinarias-boletin.html")

        mes = MESES_NOMBRE_COMPLETO[int(dt.strftime(dt.now(), "%m")) - 1]

        boletines = []
        for row in get_datos_boletines(self, premensaje=False):
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
                logger.info(
                    f"Boletin (IdMember = {row['IdMember']}) generado correctamente."
                )
                logger.debug(f"Boletin generado: {mensaje}")
                boletines.append(mensaje)

                # solo para ver html
                path = os.path.join(
                    NETWORK_PATH, "outbound", "temp", f"bol_{uuid.uuid4().hex[:8]}.html"
                )
                with open(path, "w", encoding="utf-8") as file:
                    file.write(mensaje["html"])

        if boletines:
            # guardar data en archivo (reemplaza al anterior)
            path = os.path.join(NETWORK_PATH, "outbound", "boletines_pendientes.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump(boletines, file, indent=4)
                logger.info(
                    f"Archivo 'boletines_pendientes.json' grabado correctamente. Total boletines = {len(boletines)}"
                )

        return True

    except Exception as e:
        logger.warning(f"Error generando boletines: {e}")
        return False


def redactar_boletin(cursor, IdMember, template, subject, correo):
    """
    Arma toda la información necesaria para un mensaje HTML individual.
    """

    data_servicios = generar_data_servicios(cursor, correo)

    from pprint import pprint

    pprint(data_servicios)

    return {
        "to": correo,
        "bcc": "gabfre@gmail.com",
        "subject": subject,
        "idMember": int(IdMember),
        "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hashcode": f"{str(uuid.uuid4())[-12:]}",
        "attachment_paths": [],
        "reset_next_send": 1,
        "html": template.render(payload=data_servicios),
    }


def main(self, tipo_mensaje):
    if tipo_mensaje == "alerta":
        alertas(self)
    elif tipo_mensaje == "boletin":
        boletines(self)
