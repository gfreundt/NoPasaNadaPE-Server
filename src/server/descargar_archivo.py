import base64
from datetime import datetime as dt
from flask import current_app, session, redirect, url_for, Response


def main(tipo, id):
    """
    Endpoint del sistema que procesa solicitudes para descargas de archivos.
    Extrae la data de la base de datos (bytes) y la transforma en formato PDF.
    """

    # evita navegaciones directas
    if session.get("etapa") != "validado" or not session.get("usuario"):
        return redirect(url_for("maquinarias-login"))

    db = current_app.db

    allowed_tables = {
        "DataApesegSoats": {
            "id_field": "PlacaValidate",
            "filename": f"Certificado SOAT {id}.pdf",
        },
        "DataSunarpFichas": {
            "id_field": "PlacaValidate",
            "filename": f"Ficha SUNARP {id}.pdf",
        },
        "DataMtcRecordsConductores": {
            "id_field": "IdMember_FK",
            "filename": f"Record Conductor {dt.now().strftime('%d-%m-%Y')}.pdf",
        },
    }

    config = allowed_tables.get(tipo)
    if not config:
        return "Tipo de archivo no permitido.", 400

    cursor = db.cursor()
    cmd = f"SELECT ImageBytes FROM {tipo} WHERE {config['id_field']} = ?"
    cursor.execute(cmd, (id,))
    row = cursor.fetchone()

    if not row or not row["ImageBytes"]:
        return "No se encontro archivo.", 404

    try:
        pdf_bytes = base64.b64decode(row["ImageBytes"])

        response = Response(pdf_bytes, mimetype="application/pdf")
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{config["filename"]}"'
        )
        response.headers["Content-Length"] = str(len(pdf_bytes))
        return response

    except Exception as e:
        return f"Error procesando archivo: {e}.", 500
