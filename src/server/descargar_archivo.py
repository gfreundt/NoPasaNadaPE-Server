import base64
from flask import current_app, session, redirect, url_for, Response


def main(tipo, id):

    # seguridad: evitar navegacion directa a url
    if session.get("etapa") != "validado" or not session.get("usuario"):
        return redirect(url_for("maquinarias"))

    db = current_app.db

    # extraer string base64 de la base de datos
    cursor = db.cursor()
    cmd = f"SELECT ImageBytes FROM {tipo} WHERE {'IdMember_FK' if 'Records' in tipo else 'PlacaValidate'} = ?"
    cursor.execute(cmd, (id,))
    base64_string = cursor.fetchone()

    if not base64_string:
        return "No se encontro archivo.", 404

    try:
        # decodificar base64 a formato jpeg
        image_bytes = base64.b64decode(base64_string["ImageBytes"])

        # crear nombre descriptivo
        if tipo == "DataApesegSoats":
            filename = f"Certificado SOAT {id}.jpg"
        elif tipo == "DataSunarpFichas":
            filename = f"Ficha SUNARP {id}.jpg"
        elif tipo == "DataMtcRecordsConductores":
            filename = f"Record Conductor {id}.pdf"
        else:
            filename = f"download_{tipo}_{id}.jpg"

        # devolver para la descarga
        response = Response(image_bytes, mimetype="image/jpeg")
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        return f"Error procesando archivo: {e}.", 500
