from jinja2 import Environment, FileSystemLoader
from datetime import datetime as dt
from src.utils.email import Email
from security.keys import ZEPTOMAIL_INFO_TOKEN


def activacion(db, correo, nombre=None):

    cursor, conn = db.cursor(), db.conn

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-maquinarias-activacion.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        cursor=cursor,
        conn=conn,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # crear contenido del correo
    msg = {
        "to_address": correo,
        "bcc": "gabfre@gmail.com",
        "subject": "Te invitaron a No Pasa Nada PE",
        "html_content": template.render(
            {"nombre": nombre, "ano": dt.strftime(dt.now(), "%Y")}
        ),
    }

    # enviar
    return email.send_zeptomail(msg)


def desactivacion(db, correo, nombre):

    cursor, conn = db.cursor(), db.conn

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-maquinarias-desactivacion.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        cursor=cursor,
        conn=conn,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # crear contenido del correo
    msg = {
        "to_address": correo,
        "bcc": "gabfre@gmail.com",
        "subject": "Gracias por haber sido parte de No Pasa Nada PE",
        "html_content": template.render(
            {"nombre": nombre, "ano": dt.strftime(dt.now(), "%Y")}
        ),
    }

    # enviar
    return email.send_zeptomail(msg)


def inscripcion(db, correo, nombre, placas):

    cursor, conn = db.cursor(), db.conn

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-maquinarias-inscripcion.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        cursor=cursor,
        conn=conn,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # crear contenido del correo
    msg = {
        "to_address": correo,
        "bcc": "gabfre@gmail.com",
        "subject": "Bienvenido a No Pasa Nada PE",
        "html_content": template.render(
            {
                "nombre": nombre,
                "ano": dt.strftime(dt.now(), "%Y"),
                "placas": placas,
            }
        ),
    }

    # enviar
    return email.send_zeptomail(msg)


def eliminacion(db, correo, nombre):

    cursor, conn = db.cursor(), db.conn

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-maquinarias-eliminacion.html")

    # crea objeto para enviar correo desde info@
    email = Email(
        cursor=cursor,
        conn=conn,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # crear contenido del correo
    msg = {
        "to_address": correo,
        "bcc": "gabfre@gmail.com",
        "subject": "Adios de No Pasa Nada PE",
        "html_content": template.render(
            {"nombre": nombre, "ano": dt.strftime(dt.now(), "%Y")}
        ),
    }

    # enviar
    return email.send_zeptomail(msg)


def recuperacion_contrasena(db, correo, token):

    cursor, conn = db.cursor(), db.conn

    # crear URL unico para recuperacion de contraseña
    url = f"http://localhost:5000/recuperar-contrasena/{token}"
    url = f"https://dev.nopasanadape.com/recuperar-contrasena/{token}"

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template(
        "comms-maquinarias-recuperacion-contrasena.html"
    )

    # crea objeto para enviar correo desde info@
    email = Email(
        cursor=cursor,
        conn=conn,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # crear contenido del correo
    msg = {
        "to_address": correo,
        "bcc": "gabfre@gmail.com",
        "subject": "Tu nueva contraseña de No Pasa Nada PE",
        "html_content": template.render(
            {"url": url, "ano": dt.strftime(dt.now(), "%Y")}
        ),
    }

    # enviar
    return email.send_zeptomail(msg)


def confirmacion_cambio_contrasena(db, correo):

    cursor, conn = db.cursor(), db.conn

    # load HTML templates
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template(
        "comms-maquinarias-confirmacion-cambio-contrasena.html"
    )

    # crea objeto para enviar correo desde info@
    email = Email(
        cursor=cursor,
        conn=conn,
        from_account={"name": "No Pasa Nada PE", "address": "info@nopasanadape.com"},
        token=ZEPTOMAIL_INFO_TOKEN,
    )

    # crear contenido del correo
    msg = {
        "to_address": correo,
        "bcc": "gabfre@gmail.com",
        "subject": "Tu nueva contraseña de No Pasa Nada PE",
        "html_content": template.render({"ano": dt.strftime(dt.now(), "%Y")}),
    }

    # enviar
    return email.send_zeptomail(msg)
