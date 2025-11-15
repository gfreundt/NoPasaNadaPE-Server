import os
import uuid
from jinja2 import Environment, FileSystemLoader

from src.comms import create_within_expiration, craft_messages_compose
from src.utils.constants import NETWORK_PATH


def craft(db_cursor):
    """
    Crea mensajes regulares en HTML y los guarda en /outbound.
    """

    # Actualiza tabla temporal con las expiraciones que se usarán en los mensajes
    create_within_expiration.update_table(db_cursor)

    # Carga plantilla HTML
    environment = Environment(loader=FileSystemLoader("templates/"))
    template_regular = environment.get_template("comms-regular.html")

    messages = []

    # Obtener todos los miembros que requieren mensaje tipo R
    db_cursor.execute(
        "SELECT IdMember_FK FROM _necesitan_mensajes_usuarios WHERE Tipo = 'R'"
    )

    for row in db_cursor.fetchall():
        member_id = row["IdMember_FK"]

        messages.append(
            grab_message_info(
                db_cursor=db_cursor,
                IdMember=member_id,
                template=template_regular,
                subject="Tu Boletín de No Pasa Nada PE - Noviembre 2025",
            )
        )

    # Guardar los mensajes en la carpeta outbound
    for message in messages:
        filename = f"message_{str(uuid.uuid4())[-6:]}.html"
        path = os.path.join(NETWORK_PATH, "outbound", filename)

        with open(path, "w", encoding="utf-8") as file:
            file.write(message)


def grab_message_info(db_cursor, IdMember, template, subject):
    """
    Arma toda la información necesaria para un mensaje HTML individual.
    """

    # Información del miembro
    db_cursor.execute(
        "SELECT * FROM InfoMiembros WHERE IdMember = ?", (IdMember,)
    )
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
    db_cursor.execute(
        "SELECT Placa FROM InfoPlacas WHERE IdMember_FK = ?", (IdMember,)
    )
    placas = [row["Placa"] for row in db_cursor.fetchall(_]()
