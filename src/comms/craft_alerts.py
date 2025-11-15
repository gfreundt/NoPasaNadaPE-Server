import os
from jinja2 import Environment, FileSystemLoader
from datetime import datetime as dt
import uuid

from src.utils.constants import NETWORK_PATH
from src.utils.utils import date_to_mail_format


def craft(db_cursor):
    """
    Crea el HTML de las alertas que deben ser enviadas en esta iteración y
    las guarda en el folder "outbound".
    """

    # Load HTML template
    environment = Environment(loader=FileSystemLoader("templates/"))
    template_alertas = environment.get_template("comms-alerta.html")

    # Map alert types to email codes
    index_alertas = {
        "SOAT": 1,
        "REVTEC": 3,
        "SATIMP": 5,
        "BREVETE": 7,
        "DNI": 9,
        "PASAPORTE/VISA": 11,
    }

    alerts = []

    # Pull alert requirements
    db_cursor.execute(
        """
        SELECT IdMember_FK, TipoAlerta, Vencido, FechaHasta, Placa, DocTipo
        FROM _necesitan_alertas
        """
    )

    for (
        idmember,
        tipo_alerta,
        vencido,
        fecha_hasta,
        placa,
        doc_tipo,
    ) in db_cursor.fetchall():

        if not idmember:
            continue

        alerts.append(
            compose_message(
                db_cursor=db_cursor,
                idmember=idmember,
                template=template_alertas,
                subject="ALERTA de No Pasa Nada PE",
                msg_type=index_alertas.get(tipo_alerta),
                tipo_alerta=tipo_alerta,
                vencido=vencido,
                fecha_hasta=fecha_hasta,
                placa=placa,
                doc_tipo=doc_tipo,
            )
        )

    # Save alerts in outbound folder
    for k, alert in enumerate(alerts):
        if alert:
            out_path = os.path.join(NETWORK_PATH, "outbound", f"alert_{k:03d}.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(alert)


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
    """Construye el HTML final usando la plantilla Jinja2."""

    # Secure SELECT
    db_cursor.execute("SELECT * FROM InfoMiembros WHERE IdMember = ?", (idmember,))
    member = db_cursor.fetchone()

    if not member:
        return None

    # Random hash for tracking
    email_id = f"{member['CodMember']}|{uuid.uuid4().hex[-12:]}"

    # Determine alert text
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

    else:
        _t = tipo_alerta  # fallback if DB contains an unexpected type

    estado = "ha vencido" if vencido else "está cerca de vencer"
    fecha_fmt = date_to_mail_format(fecha_hasta)

    texto_alerta = f"Tu {_t} {estado} el {fecha_fmt}."

    # Build final data injection dict
    info = {
        "nombre_usuario": member["NombreCompleto"],
        "codigo_correo": email_id,
        "titulo_alerta": titulo_alerta,
        "texto_alerta": texto_alerta,
        "vencido": vencido,
        "to": member["Correo"],
        "bcc": "gabfre@gmail.com",
        "subject": subject,
        "msg_types": [msg_type],
        "idMember": int(member["IdMember"]),
        "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hashcode": f"{member['CodMember']}|{uuid.uuid4().hex[-12:]}",
        "attachment_paths": [],
        "reset_next_send": 0,
    }

    return template.render(info)
