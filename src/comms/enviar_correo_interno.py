from jinja2 import Environment, FileSystemLoader

from src.utils.email import Email
from security.keys import ZEPTOMAIL_INFO_TOKEN
import logging

logger = logging.getLogger(__name__)


def informe_diario(cursor, mensaje, titulo):

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-interno-informe-diario.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        cursor=None,
        conn=None,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
        registro_en_bd=False,
    )

    # crear contenido del correo
    msg = {
        "to_address": "gfreundt@gmail.com",
        "bcc": "gabfre@gmail.com",
        "subject": "Informe Diario NoPasaNadaPE",
        "html_content": template.render(titulo=titulo, mensaje=mensaje),
    }

    # enviar
    logger.info("Enviando Correo Resumen")
    return email.send_zeptomail(msg)


def prueba_scrapers(mensaje, titulo):

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-interno-informe-scrapers.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        cursor=None,
        conn=None,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
        registro_en_bd=False,
    )

    # crear contenido del correo
    msg = {
        "to_address": "gfreundt@gmail.com",
        "bcc": "gabfre@gmail.com",
        "subject": "Resultado de Scrapers",
        "html_content": template.render(titulo=titulo, mensaje=mensaje),
    }

    # enviar
    return email.send_zeptomail(msg)
