from threading import Thread
from jinja2 import Environment, FileSystemLoader
from src.utils.email import Email
from src.utils.constants import ZOHO_INFO_PASSWORD


def send_code(codigo, correo, nombre):

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-codigo.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        from_account=("No Pasa Nada PE", "info@nopasanadape.com"),
        password=ZOHO_INFO_PASSWORD,
    )

    # crear contenido del correo
    msg = {
        "to": correo,
        "bcc": "gabfre@gmail.com",
        "from": email.from_account,
        "subject": "Código Único de Validación",
        "html_content": template.render({"codigo": codigo, "nombre": nombre}),
    }

    # enviar
    email.send_email(msg)


def send_welcome(correo, nombre):

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-bienvenida.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        from_account=("No Pasa Nada PE", "info@nopasanadape.com"),
        password=ZOHO_INFO_PASSWORD,
    )

    # crear contenido del correo
    msg = {
        "to": correo,
        "bcc": "gabfre@gmail.com",
        "from": email.from_account,
        "subject": "Bienvenido a No Pasa Nada PE",
        "html_content": template.render({"nombre": nombre}),
    }

    # enviar
    email.send_email(msg)


def send_cancel(correo, nombre):

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-anulacion.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        from_account=("No Pasa Nada PE", "info@nopasanadape.com"),
        password=ZOHO_INFO_PASSWORD,
    )

    # crear contenido del correo
    msg = {
        "to": correo,
        "bcc": "gabfre@gmail.com",
        "from": email.from_account,
        "subject": "Anulación de Cuenta de No Pasa Nada PE",
        "html_content": template.render({"nombre": nombre}),
    }

    # enviar
    email.send_email(msg)
