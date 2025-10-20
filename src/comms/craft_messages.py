import os
from jinja2 import Environment, FileSystemLoader
import uuid
from src.comms import create_within_expiration, craft_messages_compose
from src.utils.constants import NETWORK_PATH


def craft(db_cursor):

    # update table with all expiration information for message alerts
    create_within_expiration.update_table(db_cursor)

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template_regular = environment.get_template("comms-regular.html")

    messages = []

    # loop all members that required a regular message
    db_cursor.execute(
        "SELECT IdMember_FK FROM _necesitan_mensajes_usuarios WHERE Tipo = 'R'"
    )
    for member in db_cursor.fetchall():
        messages.append(
            grab_message_info(
                db_cursor,
                member["IdMember_FK"],
                template=template_regular,
                subject="Tu Boletín de No Pasa Nada PE - Septiembre 2025",
            )
        )

    # save crafted messages as HTML in outbound folder
    for message in messages:
        _file_path = os.path.join(
            NETWORK_PATH, "outbound", f"message_{str(uuid.uuid4())[-6:]}.html"
        )
        with open(_file_path, "w", encoding="utf-8") as file:
            file.write(message)


def grab_message_info(db_cursor, IdMember, template, subject):

    # get member information
    db_cursor.execute(f"SELECT * FROM InfoMiembros WHERE IdMember = {IdMember}")
    member = db_cursor.fetchone()

    # get message alerts
    db_cursor.execute(
        f"SELECT TipoAlerta, Placa, Vencido FROM _expira30dias WHERE IdMember = {IdMember}"
    )
    _a = db_cursor.fetchall()
    alertas = (
        [[i["TipoAlerta"], i["Placa"], i["Vencido"]] for i in _a if i] if _a else []
    )

    # get placas associated with member
    db_cursor.execute(f"SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {IdMember}")
    placas = [i["Placa"] for i in db_cursor.fetchall()]

    # generate random email hash
    email_id = f"{member['CodMember']}|{str(uuid.uuid4())[-12:]}"

    # create html format data
    return craft_messages_compose.compose(
        db_cursor, member, template, email_id, subject, alertas, placas
    )
