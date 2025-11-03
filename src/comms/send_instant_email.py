from threading import Thread
from jinja2 import Environment, FileSystemLoader
from src.utils.email import Email
from src.utils.constants import ZEPTOMAIL_INFO_TOKEN


def send_code(codigo, correo, nombre):

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-codigo.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # crear contenido del correo
    msg = {
        "to_address": correo,
        "bcc": "gabfre@gmail.com",
        "subject": "Código Temporal de Validación",
        "html_content": template.render({"codigo": codigo, "nombre": nombre}),
    }

    # enviar
    response = email.send_zeptomail(msg)


def send_welcome(correo, nombre):

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-bienvenida.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # crear contenido del correo
    msg = {
        "to_address": correo,
        "bcc": "gabfre@gmail.com",
        "subject": "Bienvenido a No Pasa Nada PE",
        "html_content": template.render({"nombre": nombre}),
    }

    # enviar
    response = email.send_zeptomail(msg)


def send_cancel(correo, nombre):

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-anulacion.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # crear contenido del correo
    msg = {
        "to_address": correo,
        "bcc": "gabfre@gmail.com",
        "subject": "Anulación de Cuenta de No Pasa Nada PE",
        "html_content": template.render({"nombre": nombre}),
    }

    # enviar
    response = email.send_zeptomail(msg)
