import smtplib
from email.message import EmailMessage
from email.utils import formataddr
import requests
from datetime import datetime as dt
from pprint import pprint


class Email:

    def __init__(self, cursor, conn, from_account, token):
        self.from_account = from_account
        self.token = token
        self.cursor = cursor
        self.conn = conn

    def send_email(self, emails):

        # if user sends single email, change format to list
        if type(emails) is not list:
            emails = [emails]

        for email in emails:
            # create the email message
            msg = EmailMessage()
            msg["From"] = (
                formataddr(self.from_account)
                if isinstance(self.from_account, tuple)
                else self.from_account
            )
            msg["To"] = email["to"]
            msg["Subject"] = email["subject"]

            # add plain text / HTML
            if email.get("plain_content"):
                msg.set_content(email["plain_content"])
            if email.get("html_content"):
                msg.add_alternative(email["html_content"], subtype="html")

            # process attachments
            if email.get("attachments"):
                for attachment in email["attachments"]:
                    msg.add_attachment(
                        attachment["bytes_data"],
                        maintype=attachment["maintype"],
                        subtype=attachment["subtype"],
                        filename=attachment["filename"],
                    )

            # send the email via Zoho's SMTP server
            try:
                with smtplib.SMTP("smtp.zoho.com", 587) as server:
                    server.starttls()  # Secure the connection
                    server.login(self.from_account[1], self.password)
                    server.send_message(msg)
                    return True
            except Exception:
                return False

    def send_zeptomail(self, email, simulation=False):

        url = "https://api.zeptomail.com/v1.1/email"

        payload = {
            "from": {
                "address": self.from_account["address"],
                "name": self.from_account["name"],
            },
            "to": [
                {
                    "email_address": {
                        "address": email["to_address"],
                        "name": "",
                    }
                }
            ],
            "subject": email["subject"],
            "htmlbody": email["html_content"],
            "attachments": email.get("attachments", []),
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": self.token,
        }

        if not simulation:

            respuesta = requests.request(
                "POST", url, json=payload, headers=headers
            ).json()
            if respuesta.get("error"):
                response_request_id = respuesta["error"].get("request_id")
                response_message = "ERROR"
            else:
                response_request_id = respuesta.get("request_id")
                response_message = "OK"
            self.registrar_envio_bd(email, response_request_id, response_message)

        else:

            response_message = "OK"
            pprint(headers)
            pprint(payload)

        # responder True si ok con la progrmacion de envio del mensaje
        return response_message == "OK"

    def registrar_envio_bd(self, mensaje, response_request_id, response_message):

        cmd = """
                    INSERT INTO StatusMensajesEnviados
                    (IdMember, TipoMensaje, DireccionCorreo, Bcc, Subject, FechaCreacion, FechaEnvio, HashCode, RespuestaId, RespuestaMensaje)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                  """

        self.cursor.execute(
            cmd,
            (
                mensaje.get("id_member"),
                mensaje.get("tipo_mensaje"),
                mensaje.get("to_address"),
                mensaje.get("bcc"),
                mensaje.get("subject"),
                mensaje.get("fecha_creacion"),
                dt.now(),
                mensaje.get("hashcode"),
                response_request_id,
                response_message,
            ),
        )

        self.conn.commit()
