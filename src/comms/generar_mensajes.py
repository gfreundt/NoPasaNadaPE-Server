import os
import uuid
from jinja2 import Environment, FileSystemLoader
from datetime import datetime as dt

from src.comms import redactar_boletines
from src.utils.constants import NETWORK_PATH
from src.utils.utils import date_to_mail_format


def alertas(db_cursor, lista_de_alertas):
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

    # # Pull alert requirements
    # db_cursor.execute(
    #     """
    #     SELECT IdMember_FK, TipoAlerta, Vencido, FechaHasta, Placa, DocTipo
    #     FROM _actualizar_alertas
    #     """
    # )

    for row in lista_de_alertas:

        if not row["IdMember"]:
            continue

        alerts.append(
            redactar_alerta(
                db_cursor=db_cursor,
                idmember=row["IdMember"],
                template=template_alertas,
                subject="ALERTA de No Pasa Nada PE",
                msg_type=index_alertas.get(row["TipoAlerta"]),
                tipo_alerta=row["TipoAlerta"],
                vencido=row["Vencido"],
                fecha_hasta=row["FechaHasta"],
                placa=row["Placa"],
                doc_tipo=row["DocTipo"],
                doc_num=row["DocNum"],
            )
        )

    # Save alerts in outbound folder
    for k, alert in enumerate(alerts):
        if alert:
            out_path = os.path.join(NETWORK_PATH, "outbound", f"alert_{k:03d}.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(alert)

    return alerts


def redactar_alerta(
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
    doc_num,
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


def boletines(db_cursor, lista_de_boletines):
    """
    Crea mensajes regulares en HTML y los guarda en /outbound.
    """

    # Carga plantilla HTML
    environment = Environment(loader=FileSystemLoader("templates/"))
    template_regular = environment.get_template("comms-regular.html")

    boletines = []
    for row in lista_de_boletines:
        member_id = row["IdMember"]

        boletines.append(
            obtener_datos(
                db_cursor=db_cursor,
                IdMember=member_id,
                template=template_regular,
                subject="Tu Boletín de No Pasa Nada PE - Noviembre 2025",
            )
        )

    # Guardar los mensajes en la carpeta outbound
    for boletin in boletines:
        filename = f"message_{str(uuid.uuid4())[-6:]}.html"
        path = os.path.join(NETWORK_PATH, "outbound", filename)

        with open(path, "w", encoding="utf-8") as file:
            file.write(boletin)

    return list(boletines)


def obtener_datos(db_cursor, IdMember, template, subject):
    """
    Arma toda la información necesaria para un mensaje HTML individual.
    """

    # Información del miembro
    db_cursor.execute("SELECT * FROM InfoMiembros WHERE IdMember = ?", (IdMember,))
    member = db_cursor.fetchone()
    if not member:
        return ""  # evita crasheos si el IdMember está huérfano

    # Alertas (tipo, placa, vencido)
    db_cursor.execute(
        "SELECT TipoAlerta, Placa, Vencido FROM _expira30dias WHERE IdMember = ?",
        (IdMember,),
    )
    alertas_raw = db_cursor.fetchall()
    alertas = (
        [[row["TipoAlerta"], row["Placa"], row["Vencido"]] for row in alertas_raw]
        if alertas_raw
        else []
    )

    # Placas asociadas
    db_cursor.execute("SELECT Placa FROM InfoPlacas WHERE IdMember_FK = ?", (IdMember,))
    placas = [row["Placa"] for row in db_cursor.fetchall()]

    # Generar hash único para email tracking
    email_id = f"{member['CodMember']}|{str(uuid.uuid4())[-12:]}"

    # Crear HTML final usando tu mega función compose()
    return redactar_boletines.compose(
        db_cursor=db_cursor,
        member=member,
        template=template,
        email_id=email_id,
        subject=subject,
        alertas=alertas,
        placas=placas,
    )
