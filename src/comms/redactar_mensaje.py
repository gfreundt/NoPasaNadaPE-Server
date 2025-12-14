from datetime import datetime as dt
from src.utils.utils import date_to_mail_format
import uuid
from src.ui.maquinarias.servicios import generar_data_servicios


def alerta(
    db_cursor,
    idmember,
    template,
    subject,
    tipo_alerta,
    vencido,
    fecha_hasta,
    placa,
    doc_tipo,
    doc_num,
):
    """Construye el HTML final usando la plantilla Jinja2."""

    # Secure SELECT
    db_cursor.execute(
        "SELECT NombreCompleto, Correo, IdMember, CodMemberInterno FROM InfoMiembros WHERE IdMember = ? LIMIT 1",
        (idmember,),
    )
    member = db_cursor.fetchone()

    if not member:
        return None

    # Random hash for tracking
    email_id = f"{member['CodMemberInterno']}|{uuid.uuid4().hex[-12:]}"

    if tipo_alerta == "BREVETE":
        servicio = "Licencia de Conducir"
        genero = "O"

    elif tipo_alerta == "REVTEC":
        servicio = "Revisión Técnica"
        genero = "A"

    elif tipo_alerta == "SOAT":
        servicio = "Certificado SOAT"
        genero = "O"

    elif tipo_alerta == "SATIMP":
        servicio = "Impuesto Vehicular SAT Lima"
        genero = "O"

    elif tipo_alerta == "DNI":
        servicio = "Documento Nacional de Identidad"
        genero = "O"

    elif tipo_alerta == "PASAPORTE/VISA":
        servicio = f"Pasaporte/Visa de {doc_tipo}"
        genero = "O"

    else:
        servicio = tipo_alerta  # fallback if DB contains an unexpected type

    # Build final data injection dict
    info = {
        "nombre_usuario": member["NombreCompleto"],
        "fecha_hasta": date_to_mail_format(fecha_hasta),
        "genero": genero,
        "servicio": servicio,
        "placa": placa,
        "vencido": vencido,
        "ano": dt.strftime(dt.now(), "%Y"),
    }

    return {
        "to": member["Correo"],
        "bcc": "gabfre@gmail.com",
        "subject": subject,
        "idMember": int(member["IdMember"]),
        "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hashcode": email_id,
        "attachment_paths": [],
        "reset_next_send": 0,
        "html": template.render(info),
    }


def boletin(db_cursor, member, template, email_id, subject, alertas, placas, correo):

    x = generar_data_servicios(db_cursor, correo)
    from pprint import pprint

    pprint(x)

    # # Build final data injection dict
    # info = {
    #     "nombre_usuario": member["NombreCompleto"],
    #     "fecha_hasta": date_to_mail_format(fecha_hasta),
    #     "genero": genero,
    #     "servicio": servicio,
    #     "placa": placa,
    #     "vencido": vencido,
    #     "ano": dt.strftime(dt.now(), "%Y"),
    # }

    return {
        "to": member["Correo"],
        "bcc": "gabfre@gmail.com",
        "subject": subject,
        "idMember": int(member["IdMember"]),
        "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hashcode": email_id,
        "attachment_paths": [],
        "reset_next_send": 0,
        "html": template.render(x),
    }

    _txtal = []
    _attachments = []
    _attach_txt = []
    _info = {}

    # create list of alerts
    for i in alertas:
        match i[0]:
            case "BREVETE":
                _txtal.append(
                    f"Licencia de Conducir {'vencida.' if i[2] else 'vence en menos de 30 días.'}"
                )
            case "SOAT":
                _txtal.append(
                    f"Certificado SOAT de placa {i[1]} {'vencido.' if i[2] else 'vence en menos de 30 días.'}"
                )
            case "SATIMP":
                _txtal.append(
                    f"Impuesto Vehicular SAT {'vencido.' if i[2] else 'vence en menos de 30 días.'}"
                )
            case "REVTEC":
                _txtal.append(
                    f"Revision Técnica de placa {i[1]} {'vencida.' if i[2] else 'vence en menos de 30 días.'}"
                )
            case "SUTRAN":
                _txtal.append(f"Multa impaga en SUTRAN para placa {i[1]}.")
            case "SATMUL":
                _txtal.append(f"Multa impaga en SAT para {i[1]}.")
            case "MTCPAPELETA":
                _txtal.append("Papeleta Impaga reportada en el MTC.")

    # add list of Alertas or "Ninguna" if empty
    _info.update({"alertas": _txtal if _txtal else ["Ninguna"]})

    # add randomly generated email ID, nombre and lista placas for opening text
    _info.update(
        {
            "nombre_usuario": member[2],
            "codigo_correo": email_id,
            "lista_placas": placas,
            "usuario": member["Correo"],
            "password": member["Password"],
        }
    )

    # get last update for all categories for the member and placa
    db_cursor.execute(f"SELECT * FROM InfoMiembros WHERE IdMember = {member[0]}")
    _data = db_cursor.fetchone()
    actualizado = {
        "brevete": date_to_mail_format(_data["LastUpdateMtcBrevetes"], elapsed=True),
        "record_conductor": date_to_mail_format(
            _data["LastUpdateMtcRecordsConductores"], elapsed=True
        ),
        "satimp": date_to_mail_format(
            _data["LastUpdateSatImpuestosCodigos"], elapsed=True
        ),
    }
    db_cursor.execute(
        f"SELECT * FROM InfoPlacas WHERE IdMember_FK = {member[0]} LIMIT 1"
    )
    _data = db_cursor.fetchone()
    actualizado.update(
        {
            "soat": (
                date_to_mail_format(_data["LastUpdateApesegSoats"], elapsed=True)
                if _data
                else ""
            ),
            "revtec": (
                date_to_mail_format(
                    _data["LastUpdateMtcRevisionesTecnicas"], elapsed=True
                )
                if _data
                else ""
            ),
            "sunarp": (
                date_to_mail_format(_data["LastUpdateSunarpFichas"], elapsed=True)
                if _data
                else ""
            ),
        }
    )
    _info.update({"actualizado": actualizado})

    # add revision tecnica information
    db_cursor.execute(
        f"SELECT * FROM DataMtcRevisionesTecnicas WHERE PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {member[0]}) ORDER BY LastUpdate DESC"
    )
    _revtecs = []

    for _m in db_cursor.fetchall():

        _revtecs.append(
            {
                "certificadora": _m["Certificadora"].split("-")[-1][:35],
                "placa": _m["PlacaValidate"],
                "certificado": _m["Certificado"],
                "fecha_desde": date_to_mail_format(_m["FechaDesde"]),
                "fecha_hasta": date_to_mail_format(_m["FechaHasta"], delta=True),
                "resultado": _m["Resultado"],
                "vigencia": _m["Vigencia"],
                "actualizado": actualizado["revtec"],
            }
        )
    _info.update({"revtecs": _revtecs})

    # add brevete information
    db_cursor.execute(
        f"SELECT * FROM DataMtcBrevetes WHERE IdMember_FK = {member[0]} ORDER BY LastUpdate DESC"
    )
    _m = db_cursor.fetchone()
    if _m:
        _info.update(
            {
                "brevete": {
                    "numero": _m["Numero"],
                    "clase": _m["Clase"],
                    "formato": _m["Tipo"],
                    "fecha_desde": date_to_mail_format(_m["FechaExp"]),
                    "fecha_hasta": date_to_mail_format(_m["FechaHasta"], delta=True),
                    "restricciones": _m["Restricciones"],
                    "local": _m["Centro"],
                    "puntos": _m["Puntos"],
                    "record": _m["Record"],
                    "actualizado": actualizado["brevete"],
                }
            }
        )
    else:
        _info.update({"brevete": {}})

    # add SUTRAN information
    _sutran = []
    db_cursor.execute(
        f"SELECT * FROM DataSutranMultas JOIN InfoPlacas ON Placa = PlacaValidate WHERE Placa IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {member[0]}) ORDER BY LastUpdate DESC"
    )
    for _m in db_cursor.fetchall():
        if _m:
            _sutran.append(
                {
                    "placa": _m[9],
                    "documento": _m[1],
                    "tipo": _m[2],
                    "fecha_documento": date_to_mail_format(_m[3]),
                    "infraccion": (f"{_m[4]} - {_m[5]}"),
                    "actualizado": actualizado["sutran"],
                }
            )
        _info.update({"sutrans": _sutran})

    # add SATIMP information
    db_cursor.execute(
        f"SELECT * FROM DataSatImpuestosCodigos WHERE IdMember_FK = {member[0]} ORDER BY LastUpdate DESC"
    )

    _v = []
    for satimp in db_cursor.fetchall():
        _lu = actualizado["satimp"]
        db_cursor.execute(
            f"SELECT * FROM DataSatImpuestosDeudas WHERE Codigo = {satimp[1]} ORDER BY DocNum ASC"
        )
        _s = []
        for _x in db_cursor.fetchall():
            _s.append(
                {
                    "ano": _x[1],
                    "periodo": _x[2],
                    "doc_num": _x[3],
                    "total_a_pagar": _x[4],
                    "actualizado": _lu,
                }
            )
        _v.append({"codigo": satimp[1], "deudas": _s})
    _info.update({"satimps": _v})

    # add SOAT information
    _soats = []
    db_cursor.execute(
        f"SELECT * FROM DataApesegSoats WHERE PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {member[0]}) ORDER BY LastUpdate DESC"
    )
    for _m in db_cursor.fetchall():
        _soats.append(
            {
                "aseguradora": _m[1],
                "fecha_desde": date_to_mail_format(_m[2]),
                "fecha_hasta": date_to_mail_format(_m[3], delta=True),
                "certificado": _m[5],
                "placa": _m[4],
                "uso": _m[6],
                "clase": _m[7],
                "vigencia": _m[8],
                "tipo": _m[9],
                "actualizado": actualizado["soat"],
            }
        )
        # add image to attachment list
        if _m["ImageBytes"]:
            _attachments.append(
                {
                    "filename": f'SOAT {_m["PlacaValidate"]}.jpg',
                    "bytes": _m["ImageBytes"],
                    "type": "image/jpeg",
                }
            )
            _attach_txt.append(
                f"Certificado Electrónico SOAT de Vehículo Placa {_m[4]}."
            )
    _info.update({"soats": _soats})

    # add SATMUL information
    _satmuls = []
    db_cursor.execute(
        f"SELECT * FROM DataSatMultas WHERE PlacaValidate IN (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = {member[0]}) ORDER BY LastUpdate DESC"
    )
    for n, _m in enumerate(db_cursor.fetchall()):
        _satmuls.append(
            {
                "placa": _m[1],
                "reglamento": _m[2],
                "falta": _m[3],
                "documento": _m[4],
                "fecha_emision": date_to_mail_format(_m[5]),
                "importe": _m[6],
                "gastos": _m[7],
                "descuento": _m[8],
                "deuda": _m[9],
                "estado": _m[10],
                "licencia": _m[11],
                "actualizado": actualizado["satmul"],
            }
        )
        # add image to attachment list
        if _m["ImageBytes1"]:
            _attachments.append(
                {
                    "filename": f'Multa SAT Papeleta {_m["PlacaValidate"]} - {n+1}.jpg',
                    "bytes": _m["ImageBytes1"],
                    "type": "image/jpeg",
                }
            )
            _attach_txt.append(
                f"Papeleta de Infracción de Tránsito SAT de Vehículo Placa {_m["PlacaValidate"]}."
            )

        # add image to attachment list
        if _m["ImageBytes2"]:
            _attachments.append(
                {
                    "filename": f'Multa SAT Fotografía {_m["PlacaValidate"]} - {n+1}.jpg',
                    "bytes": _m["ImageBytes2"],
                    "type": "image/jpeg",
                }
            )
            _attach_txt.append(
                f"Fotografía de Infracción de Tránsito de Vehículo Placa {_m["PlacaValidate"]}."
            )
    _info.update({"satmuls": _satmuls})

    # add SUNARP image
    db_cursor.execute(
        f"""    SELECT * FROM DataSunarpFichas 
                WHERE PlacaValidate IN
                    (SELECT Placa FROM InfoPlacas
                        WHERE IdMember_FK = {member[0]})
                ORDER BY LastUpdate DESC"""
    )
    for _m in db_cursor.fetchall():
        # add image to attachment list
        if _m["ImageBytes"]:
            _attachments.append(
                {
                    "filename": f'Ficha SUNARP {_m["PlacaValidate"]}.jpg',
                    "bytes": _m["ImageBytes"],
                    "type": "image/jpeg",
                    "actualizado": actualizado["sunarp"],
                }
            )
            _attach_txt.append(
                f"Consulta Vehicular SUNARP de Vehículo Placa {_m["PlacaValidate"]}."
            )

    # add RECORD DE CONDUCTOR image
    db_cursor.execute(
        f"SELECT * FROM DataMtcRecordsConductores WHERE IdMember_FK = {member[0]} ORDER BY LastUpdate DESC"
    )
    for _m in db_cursor.fetchall():
        # add image to attachment list
        if _m["ImageBytes"]:
            _attachments.append(
                {
                    "filename": "Record del Conductor.pdf",
                    "bytes": _m["ImageBytes"],
                    "type": "application/pdf",
                    "actualizado": actualizado["record_conductor"],
                }
            )
            _attach_txt.append("Récord del Conductor MTC.")

    # subject title number of alerts
    _subj = (
        f"{len(_txtal)} ALERTAS"
        if len(_txtal) > 1
        else "1 ALERTA" if len(_txtal) == 1 else "SIN ALERTAS"
    )

    # meta data
    _info.update({"to": member[6]})
    _info.update({"bcc": "gabfre@gmail.com"})
    _info.update({"subject": f"{subject} ({_subj})"})
    _info.update({"idMember": int(member[0])})
    _info.update({"timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S")})
    _info.update({"hashcode": email_id})
    _info.update({"attachments": _attachments})
    _info.update({"adjuntos_titulos": _attach_txt})
    _info.update({"reset_next_send": 1})

    return template.render(_info)
