import os
from datetime import datetime as dt, timedelta as td
from bs4 import BeautifulSoup
from src.utils.email import Email
from src.utils.constants import NETWORK_PATH, ZEPTOMAIL_INFO_TOKEN


def send(db_cursor, db_conn, max=12):
    """send messages in outbound folder, limit to avoid zoho mail considering it spam"""

    result = {"ok": 0, "error": 0}

    # select all the emails in outbound folder and cap list to max amount to send
    html_files = [
        i for i in os.listdir(os.path.join(NETWORK_PATH, "outbound")) if ".html" in i
    ][:max]

    # activate send account
    email = Email(
        from_account={"name":"No Pasa Nada PE", "address":"info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # iterate on all html files in outbound folder
    for html_file in html_files:

        # open files and find all relevant elements
        with open(
            os.path.join(NETWORK_PATH, "outbound", html_file), "r", encoding="utf-8"
        ) as file:
            data = file.read()
            soup = BeautifulSoup(data, features="lxml")
            body = BeautifulSoup(data, "html.parser").find("body")

        # email requires: to, bcc, subject, html_content, attachments
        meta = soup.find_all("meta")
        msg = {
            "to_address": [i["content"] for i in meta if i["name"] == "to"][0],
            "bcc": [i["content"] for i in meta if i["name"] == "bcc"][0],
            "subject": [i["content"] for i in meta if i["name"] == "subject"][0],
            "hashcode": [i["content"] for i in meta if i["name"] == "hashcode"][0],
            "html_content": str(soup.find("body")),
            "reset_next_send": [
                int(i["content"]) for i in meta if i["name"] == "reset_next_send"
            ][0],
        }

        # parse attachments
        a = [i["content"] for i in meta if i["name"] == "attachment-filename"]
        b = [i["content"] for i in meta if i["name"] == "attachment-bytes"]
        c = [i["content"] for i in meta if i["name"] == "attachment-type"]

        attachments = [
            {
                "name": i,
                "content": j,
                "mime_type": k
            }
            for i, j, k in zip(a, b, c)
        ]

        msg.update({"attachments": attachments})

        # send
        response = email.send_zeptomail(msg)

        # register message sent in mensajes table (if email sent correctly)
        if response:
            if "alert" in html_file:
                _tipo = "Alerta"
            elif "message" in html_file:
                _tipo = (
                    "Mensaje Bienvenida" if "bienvenida" in data else "Mensaje Regular"
                )
            else:
                _tipo = "Otro"
            _now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            _next = (dt.now() + td(days=31)).strftime("%Y-%m-%d %H:%M:%S")

            # update message sent list
            db_cursor.execute(
                f"SELECT IdMember FROM InfoMiembros WHERE Correo = '{msg["to_address"]}'"
            )
            _id_member = db_cursor.fetchone()[0]

            db_cursor.execute(
                "INSERT INTO StatusMensajesEnviados (IdMember_FK, FechaEnvio, Tipo, Contenido, HashCode) VALUES (?, ?, ?, ?, ?)",
                (_id_member, _now, _tipo, str(body), msg["hashcode"]),
            )

            # update date for next message to be sent (if message requires)
            if msg.get("reset_next_send"):
                db_cursor.execute(
                    "UPDATE InfoMiembros SET ForceMsg = 0, NextMessageSend = ? WHERE Correo = ?",
                    (_next, msg["to_address"]),
                )

            db_conn.commit()

            # erase message from outbound folder
            os.remove(os.path.join(NETWORK_PATH, "outbound", html_file))
            result["ok"] += 1

        else:
            result["error"] += 1

    return result
