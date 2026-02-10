from datetime import datetime as dt
import sqlite3
import os
from pprint import pprint
from src.utils.constants import NETWORK_PATH

from flask import Flask, render_template

app = Flask(
    __name__,
    template_folder=os.path.join(NETWORK_PATH, "templates"),
    static_folder=os.path.join(NETWORK_PATH, "static"),
)


def date_to_user_format(fecha):
    # change date format to a more legible one

    _months = (
        "Ene",
        "Feb",
        "Mar",
        "Abr",
        "May",
        "Jun",
        "Jul",
        "Ago",
        "Sep",
        "Oct",
        "Nov",
        "Dic",
    )
    _day = fecha[8:]
    _month = _months[int(fecha[5:7]) - 1]
    _year = fecha[:4]

    return f"{_day}-{_month}-{_year}"


@app.route("/<correo>")
def generar_data_servicios(correo):

    conn = sqlite3.connect("./data/members.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # -------- ENCABEZADO -------- #

    cursor.execute(
        """ SELECT  IdMember, LastUpdateMtcBrevetes, LastUpdateMtcRecordsConductores,
                    LastUpdateSatImpuestos, NombreCompleto, DocTipo, DocNum
            FROM InfoMiembros
            WHERE Correo = ?
            LIMIT 1
        """,
        (correo,),
    )
    dato_miembro = cursor.fetchone()
    id_miembro = dato_miembro["IdMember"]
    ultimas_actualizaciones_miembro = {
        "brevetes": dato_miembro["LastUpdateMtcBrevetes"],
        "recvehic": dato_miembro["LastUpdateMtcRecordsConductores"],
        "satimps": dato_miembro["LastUpdateSatImpuestos"],
    }

    cursor.execute(
        """ SELECT  Placa, LastUpdateApesegSoats, LastUpdateMtcRevisionesTecnicas,
	                LastUpdateSunarpFichas, LastUpdateSutranMultas, LastUpdateSatMultas,
	                LastUpdateCallaoMultas
            FROM InfoPlacas
            WHERE IdMember_FK = ?
        """,
        (id_miembro,),
    )
    datos_placas = cursor.fetchall()
    ultimas_actualizaciones_placas = {
        i["Placa"]: {
            "soat": i["LastUpdateApesegSoats"],
            "revtec": i["LastUpdateMtcRevisionesTecnicas"],
            "sunarp": i["LastUpdateSunarpFichas"],
            "sutran": i["LastUpdateSutranMultas"],
            "satmultas": i["LastUpdateSatMultas"],
            "callaomultas": i["LastUpdateCallaoMultas"],
        }
        for i in datos_placas
    }

    encabezado = {
        "nombre": dato_miembro["NombreCompleto"],
        "tipo_documento": dato_miembro["DocTipo"],
        "numero_documento": dato_miembro["DocNum"],
        "placas": [i["Placa"] for i in datos_placas] if datos_placas else ["Ninguna"],
    }

    # -------- VENCIMIENTOS -------- #

    vencimientos = []

    # Licencia de Conducir
    cursor.execute(
        """ SELECT Numero, FechaHasta
            FROM InfoMiembros a
            LEFT JOIN DataMtcBrevetes b
            ON b.IdMember_FK = a.IdMember
            WHERE a.IdMember = ?
        """,
        (id_miembro,),
    )

    for licencia in cursor.fetchall():
        plazos = calculo_plazos(
            licencia["FechaHasta"], ultimas_actualizaciones_miembro["brevetes"]
        )
        vencimientos.append(
            plazos
            | {
                "titulo": "Licencia de Conducir",
                "subtitulo": f"Numero: {licencia['Numero']}",
                "boton_detalle": licencia["FechaHasta"] is not None,
            }
        )

    # Certificados SOAT
    cursor.execute(
        """ SELECT Placa, FechaHasta
            FROM InfoPlacas a
            LEFT JOIN DataApesegSoats b
            ON b.PlacaValidate = a.Placa
            WHERE IdMember_FK = ?
        """,
        (id_miembro,),
    )

    for soat in cursor.fetchall():
        placa = soat["Placa"]
        plazos = calculo_plazos(
            soat["FechaHasta"], ultimas_actualizaciones_placas[placa]["soat"]
        )
        vencimientos.append(
            plazos
            | {
                "titulo": "SOAT",
                "subtitulo": f"Placa: {placa}",
                "boton_detalle": soat["FechaHasta"] is not None,
            }
        )

    # Revisiones Tecnicas
    cursor.execute(
        """ SELECT Placa, FechaHasta
            FROM InfoPlacas a
            LEFT JOIN DataMtcRevisionesTecnicas b
            ON b.PlacaValidate = a.Placa
            WHERE IdMember_FK = ?
        """,
        (id_miembro,),
    )

    for revtec in cursor.fetchall():
        placa = revtec["Placa"]
        plazos = calculo_plazos(
            revtec["FechaHasta"],
            ultimas_actualizaciones_placas[placa]["revtec"],
        )
        vencimientos.append(
            plazos
            | {
                "titulo": "Revisión Técnica",
                "subtitulo": f"Placa: {placa}",
                "boton_detalle": revtec["FechaHasta"] is not None,
            }
        )

    # Impuestos SAT
    cursor.execute(
        """ SELECT a.Codigo, b.FechaHasta, b.TotalAPagar
            FROM InfoMiembros c
            LEFT JOIN DataSatImpuestosCodigos a
            ON a.IdMember_FK = c.IdMember
            LEFT JOIN DataSatImpuestosDeudas b
            ON b.Codigo = a.Codigo
            WHERE c.IdMember = ?
        """,
        (id_miembro,),
    )

    for satimp in cursor.fetchall():
        plazos = calculo_plazos(
            satimp["FechaHasta"], ultimas_actualizaciones_miembro["satimps"]
        )

        # ajustar estado a particularidad de este servicio
        if not satimp["Codigo"]:
            plazos["estado"] = "Sin Registros"
            plazos["estado_bg"] = STATUS_BG["info"]
        elif not satimp["FechaHasta"]:
            plazos["estado"] = "Sin Pagos Pendientes"
            plazos["estado_bg"] = STATUS_BG["ok"]

        vencimientos.append(
            plazos
            | {
                "titulo": "Impuestos SAT",
                "subtitulo": f"Código: {satimp['Codigo']}" if satimp["Codigo"] else "",
                "boton_detalle": satimp["FechaHasta"] is not None,
            }
        )
    # -------- MANTENIMIENTOS -------- #

    mantenimientos = [
        {
            "placa": "ABC123",
            "actividades": [
                {
                    "status": "Realizado",
                    "km": "5,000 km",
                    "fecha": date_to_user_format("2024-09-15"),
                    "boton_detalle": True,
                },
                {
                    "status": "Realizado",
                    "km": "10,000 km",
                    "fecha": date_to_user_format("2025-06-12"),
                    "boton_detalle": True,
                },
                {
                    "status": "Pendiente",
                    "km": "15,000 km",
                    "fecha": date_to_user_format("2026-09-15"),
                    "boton_detalle": False,
                },
                {
                    "status": "Pendiente",
                    "km": "25,000 km",
                    "fecha": date_to_user_format("2027-06-12"),
                    "boton_detalle": True,
                },
                {
                    "status": "Pendiente",
                    "km": "50,000 km",
                    "fecha": date_to_user_format("2028-07-10"),
                    "boton_detalle": True,
                },
            ],
            "ultima_revision": date_to_user_format("2026-01-15"),
        },
        {
            "placa": "JKL456",
            "actividades": [],
            "ultima_revision": date_to_user_format("2026-01-15"),
        },
        {
            "placa": "XYZ999",
            "actividades": [
                {
                    "status": "Realizado",
                    "km": "5,000 km",
                    "fecha": date_to_user_format("2024-09-15"),
                    "boton_detalle": True,
                },
                {
                    "status": "Realizado",
                    "km": "10,000 km",
                    "fecha": date_to_user_format("2025-06-12"),
                    "boton_detalle": False,
                },
                {
                    "status": "Pendiente",
                    "km": "15,000 km",
                    "fecha": date_to_user_format("2026-09-15"),
                    "boton_detalle": True,
                },
                {
                    "status": "Pendiente",
                    "km": "25,000 km",
                    "fecha": date_to_user_format("2027-06-12"),
                    "boton_detalle": True,
                },
                {
                    "status": "Pendiente",
                    "km": "50,000 km",
                    "fecha": date_to_user_format("2028-07-10"),
                    "boton_detalle": False,
                },
            ],
            "ultima_revision": date_to_user_format("2026-01-15"),
        },
    ]

    # -------- MULTAS -------- #

    existentes = []

    # SAT Multas
    cursor.execute(
        """ SELECT
            PlacaValidate, Falta, FechaEmision, Deuda, Estado, LastUpdate
            FROM
            DataSatMultas
            WHERE
            PlacaValidate IN
                (SELECT Placa
                FROM InfoPlacas
                WHERE IdMember_FK = ?)
        """,
        (id_miembro,),
    )

    for satmul in cursor.fetchall():
        existentes.append(
            {
                "titulo": "SAT Lima",
                "subtitulo": f"Placa: {satmul['PlacaValidate']}",
                "fecha": date_to_user_format(satmul["FechaEmision"]),
                "falta": satmul["Falta"],
                "situacion": {
                    "titulo": satmul["Estado"],
                    "subtitulo": f"S/{satmul['Deuda']}",
                },
                "ultima_actualizacion": {
                    "fecha": date_to_user_format(satmul["LastUpdate"]),
                    "dias_desde": f"{
                        (dt.now() - dt.strptime(satmul['LastUpdate'], '%Y-%m-%d')).days
                    } días",
                },
                "boton_detalle": True,
            }
        )

    # SUTRAN Multas
    cursor.execute(
        """ SELECT
            PlacaValidate, CodigoInfrac, FechaDoc, Clasificacion, LastUpdate
            FROM
            DataSutranMultas
            WHERE
            PlacaValidate IN
                (SELECT Placa
                FROM InfoPlacas
                WHERE IdMember_FK = ?)
        """,
        (id_miembro,),
    )

    for sutran in cursor.fetchall():
        existentes.append(
            {
                "titulo": "SUTRAN",
                "subtitulo": f"Placa: {sutran['PlacaValidate']}",
                "fecha": date_to_user_format(sutran["FechaDoc"]),
                "falta": sutran["CodigoInfrac"],
                "situacion": {
                    "titulo": sutran["Clasificacion"],
                    "subtitulo": "",
                },
                "ultima_actualizacion": {
                    "fecha": date_to_user_format(sutran["LastUpdate"]),
                    "dias_desde": f"{
                        (dt.now() - dt.strptime(sutran['LastUpdate'], '%Y-%m-%d')).days
                    } días",
                },
                "boton_detalle": True,
            }
        )

    # Callao Multas
    cursor.execute(
        """ SELECT
            PlacaValidate, Codigo, FechaInfraccion, TotalInfraccion, TotalBeneficio, LastUpdate
            FROM
            DataCallaoMultas
            WHERE
            PlacaValidate IN
                (SELECT Placa
                FROM InfoPlacas
                WHERE IdMember_FK = ?)
        """,
        (id_miembro,),
    )

    for calmul in cursor.fetchall():
        existentes.append(
            {
                "titulo": "Municipalidad del Callao",
                "subtitulo": f"Placa: {calmul['PlacaValidate']}",
                "fecha": date_to_user_format(calmul["FechaInfraccion"]),
                "falta": calmul["Codigo"],
                "situacion": {
                    "titulo": f"Total: S/{calmul['TotalInfraccion']}",
                    "subtitulo": f"Descontada: S/{calmul['TotalBeneficio']}",
                },
                "ultima_actualizacion": {
                    "fecha": date_to_user_format(calmul["LastUpdate"]),
                    "dias_desde": f"{
                        (dt.now() - dt.strptime(calmul['LastUpdate'], '%Y-%m-%d')).days
                    } días",
                },
                "boton_detalle": True,
            }
        )

    # Agregar avisos que no se encontraron multas
    avisos = []
    if not [i for i in existentes if i["titulo"] == "Multa SAT Lima"]:
        avisos.append(
            {
                "texto": "No se encontraron multas SAT Lima.",
                "fecha": f"Actualizado: {date_to_user_format(ultimas_actualizaciones_miembro['satimps'])}",
            }
        )
    if not [i for i in existentes if i["titulo"] == "Multa SUTRAN"]:
        avisos.append(
            {
                "texto": "No se encontraron multas SUTRAN.",
                "fecha": f"Actualizado: TBD",
            }
        )
    if not [i for i in existentes if i["titulo"] == "Multa Municipalidad del Callao"]:
        avisos.append(
            {
                "texto": "No se encontraron multas Municipalidad del Callao.",
                "fecha": f"Actualizado: TBD",
            }
        )
    # -------- DESCARGAS -------- #

    descargas = {}

    cursor.execute(
        """ SELECT
            PlacaValidate, lastUpdate
            FROM
            DataApesegSoats
            WHERE
            PlacaValidate IN
                (SELECT Placa
                FROM InfoPlacas
                WHERE IdMember_FK = ?)
            AND ImageBytes IS NOT NULL
        """,
        (id_miembro,),
    )

    soat = [
        {"placa": i["PlacaValidate"], "fecha": date_to_user_format(i["lastUpdate"])}
        for i in cursor.fetchall()
    ]

    descargas.update(
        {
            "soats": (
                {
                    "disponible": True,
                    "detalles": soat,
                }
                if soat
                else {
                    "disponible": False,
                    "detalles": "No Hay Certificados SOAT Disponibles.",
                }
            )
        }
    )

    cursor.execute(
        """ SELECT
            PlacaValidate, lastUpdate
            FROM
            DataSunarpFichas
            WHERE
            PlacaValidate IN
                (SELECT Placa
                FROM InfoPlacas
                WHERE IdMember_FK = ?)
            AND ImageBytes IS NOT NULL
        """,
        (id_miembro,),
    )
    sunarp = [
        {"placa": i["PlacaValidate"], "fecha": date_to_user_format(i["lastUpdate"])}
        for i in cursor.fetchall()
    ]
    descargas.update(
        {
            "sunarps": (
                {
                    "disponible": True,
                    "detalles": sunarp,
                }
                if sunarp
                else {
                    "disponible": False,
                    "detalles": "No Hay Fichas Registrales Disponibles.",
                }
            )
        }
    )

    cursor.execute(
        """ SELECT
            a.LastUpdate,
            b.DocTipo,
            b.DocNum
            FROM DataMtcRecordsConductores a
            JOIN InfoMiembros b
            ON b.IdMember = a.IdMember_FK
            WHERE a.IdMember_FK = ?
            AND a.ImageBytes IS NOT NULL
        """,
        (id_miembro,),
    )

    recvehic = [
        {
            "doc": f"{i['DocTipo']} {i['DocNum']}",
            "fecha": date_to_user_format(i["LastUpdate"]),
        }
        for i in cursor.fetchall()
    ]
    descargas.update(
        {
            "recvehic": (
                {
                    "disponible": True,
                    "detalles": recvehic,
                }
                if recvehic
                else {
                    "disponible": False,
                    "detalles": "No Hay Récords Vehiculares Disponibles.",
                }
            )
        }
    )

    # -------- METADATA -------- #

    urls = {"mi_perfil": "#", "salir": "#"}
    metadata = {"urls": urls}

    # -------- ARMADO DE RESPUESTA -------- #
    payload = {
        "encabezado": encabezado,
        "vencimientos": vencimientos,
        "mantenimientos": mantenimientos,
        "multas": {
            "existentes": existentes,
            "avisos": avisos,
        },
        "descargas": descargas,
        "metadata": metadata,
    }

    pprint(payload)

    return render_template("servicios_test.html", payload=payload)


def calculo_plazos(fecha_vigencia, fecha_actualizacion):

    # calcular dias desde ultima actualizacion
    dias_a = (dt.now() - dt.strptime(fecha_actualizacion, "%Y-%m-%d")).days

    if fecha_vigencia:
        # calcular dias restantes para vencimiento (si hay fecha) y determinar estado
        dias_v = (dt.strptime(fecha_vigencia, "%Y-%m-%d") - dt.now()).days + 1
        if dias_v < 0:
            estado = "Vencido"
            estado_bg = STATUS_BG["peligro"]
        elif dias_v <= 30:
            estado = "Por Vencer"
            estado_bg = STATUS_BG["advertencia"]
        else:
            estado = "Vigente"
            estado_bg = STATUS_BG["ok"]

        return {
            "estado": estado,
            "estado_bg": estado_bg,
            "vigencia": {
                "fecha": (
                    date_to_user_format(fecha_vigencia) if fecha_vigencia else "N/A"
                ),
                "dias_restantes": (
                    f"{dias_v:,} {'día' if dias_v == 1 else 'días'} "
                    if dias_v >= 0
                    else ""
                ),
            },
            "ultima_actualizacion": {
                "fecha": date_to_user_format(fecha_actualizacion),
                "dias_desde": f"hace {dias_a:,} {'día' if dias_a == 1 else 'días'}",
            },
        }

    else:
        return {
            "estado": "No Disponible",
            "estado_bg": STATUS_BG["info"],
            "vigencia": {
                "fecha": "N/A",
                "dias_restantes": "",
            },
            "ultima_actualizacion": {
                "fecha": date_to_user_format(fecha_actualizacion),
                "dias_desde": f"hace {dias_a:,} {'día' if dias_a == 1 else 'días'}",
            },
        }


if __name__ == "__main__":
    STATUS_BG = {
        "ok": "#d1e7dd",
        "advertencia": "#fff3cd",
        "peligro": "#f8d7da",
        "info": "#cff4fc",
    }

    colores = {
        "ok": "text-success",
        "advertencia": "text-warning",
        "peligro": "text-danger",
        "info": "text-primary",
    }
    app.run(debug=True)
