from datetime import datetime as dt
from flask import render_template, request, session, redirect, url_for

from src.utils.utils import date_to_user_format


def main(self):
    # respuesta a pings para medir uptime
    if request.method == "HEAD":
        return ("", 200)

    # seguridad: evitar navegacion directa a url
    if session.get("etapa") != "validado":
        return redirect(url_for("maquinarias"))

    # extraer toda la data relevante de la base de datos
    cursor = self.db.cursor()
    payload = generar_data_servicios(
        cursor, correo=session.get("usuario", {}).get("correo")
    )

    return render_template(
        "ui-maquinarias-mi-cuenta.html",
        payload=payload,
    )


def generar_data_servicios(cursor, correo):
    #

    STATUS_BG = {
        "ok": "#d1e7dd",
        "advertencia": "#fff3cd",
        "peligro": "#f8d7da",
        "info": "#cff4fc",
    }

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

    # -------- ENCABEZADO -------- #

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
                "subtitulo": f"Número: {licencia['Numero']}"
                if licencia["Numero"]
                else "",
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
        """ SELECT Placa, FechaHasta, AnoFabricacion
            FROM InfoPlacas a
            LEFT JOIN DataMtcRevisionesTecnicas b
            ON b.PlacaValidate = a.Placa
            WHERE IdMember_FK = ?
        """,
        (id_miembro,),
    )

    for revtec in cursor.fetchall():
        placa = revtec["Placa"]
        ano_fabricacion = revtec["AnoFabricacion"]

        if ano_fabricacion:
            fpr = fecha_primera_revtec(ano_fabricacion, placa)
            if dt.strptime(fpr, "%Y-%m-%d") > dt.now():
                pass

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
        """ SELECT Codigo, FechaHasta, TotalAPagar
            FROM InfoMiembros a
            LEFT JOIN DataSatImpuestos b 
            ON a.IdMember = b.IdMember_FK
            WHERE a.IdMember = ?
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
    mantenimientos = []

    fake_from_db = [
        {
            "Placa": "ABC123",
            "previos": [],
            "Proximos": [
                {
                    "km": "35,000 km.",
                    "FechaHasta": "2026-01-27",
                }
            ],
            "ultima_revision": "2026-01-15",
        },
        {
            "Placa": "XYZ999",
            "previos": [],
            "Proximos": [
                {
                    "km": "15,000 km.",
                    "FechaHasta": "2027-05-22",
                },
                {
                    "km": "20,000 km.",
                    "FechaHasta": "2027-08-12",
                },
            ],
            "ultima_revision": "2026-01-15",
        },
        {
            "Placa": "RJK874",
            "previos": [],
            "Proximos": [],
            "ultima_revision": "2026-01-15",
        },
    ]

    for mant in fake_from_db:
        estado_bg = STATUS_BG["ok"]
        manto = []
        placa = mant["Placa"]
        for proximo in mant["Proximos"]:
            plazos = calculo_plazos(
                fecha_vigencia=proximo["FechaHasta"],
                fecha_actualizacion="2026-01-21",  # ultimas_actualizaciones_placas[placa]["soat"]
            )
            manto.append(plazos | {"km": proximo["km"]})

            # definir color de toda la fila: cualquier rojo en subfila hace que toda la fila sea roja
            if plazos.get("estado_bg") != STATUS_BG["ok"]:
                estado_bg = plazos.get("estado_bg")

        # definir color de todas la fila: si no hay infomracion pone color info
        if not mant["Proximos"]:
            estado_bg = STATUS_BG["info"]

        mantenimientos.append(
            {
                "placa": placa,
                "info": manto,
                "ultima_actualizacion": plazos["ultima_actualizacion"],
                "estado_bg": estado_bg,
            }
        )

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
        fecha = calculo_plazos(None, ultimas_actualizaciones_miembro["satimps"])[
            "ultima_actualizacion"
        ]
        avisos.append(
            {
                "texto": "No se encontraron multas SAT Lima.",
                "fecha": f"Actualizado: {fecha['fecha']} ({fecha['dias_desde']})",
            }
        )

    if not [i for i in existentes if i["titulo"] == "Multa SUTRAN"]:
        if datos_placas:
            d = ultimas_actualizaciones_placas.get(datos_placas[0]["Placa"])
            fecha = calculo_plazos(None, d["sutran"])["ultima_actualizacion"]
        else:
            fecha["fecha"] = {"fecha": "N/A", "dias_desde": ""}

        avisos.append(
            {
                "texto": "No se encontraron multas SUTRAN.",
                "fecha": f"Actualizado: {fecha['fecha']} ({fecha['dias_desde']})",
            }
        )

    if not [i for i in existentes if i["titulo"] == "Municipalidad del Callao"]:
        if datos_placas:
            d = ultimas_actualizaciones_placas.get(datos_placas[0]["Placa"])
            fecha = calculo_plazos(None, d["callaomultas"])["ultima_actualizacion"]
        else:
            fecha["fecha"] = {"fecha": "N/A", "dias_desde": ""}

        avisos.append(
            {
                "texto": "No se encontraron multas de la Municipalidad del Callao.",
                "fecha": f"Actualizado: {fecha['fecha']} ({fecha['dias_desde']})",
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
        {
            "placa": i["PlacaValidate"],
            "fecha": f"({date_to_user_format(i['LastUpdate'])})",
            "url": f"/descargar_archivo/DataApesegSoats/{i['PlacaValidate']}",
        }
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
        {
            "placa": i["PlacaValidate"],
            "fecha": f"({date_to_user_format(i['LastUpdate'])})",
            "url": f"/descargar_archivo/DataSunarpFichas/{i['PlacaValidate']}",
        }
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
            "fecha": f"({date_to_user_format(i['LastUpdate'])})",
            "url": f"/descargar_archivo/DataMtcRecordsConductores/{id_miembro}",
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

    urls = {
        "mi_perfil": "/maquinarias/mi-perfil",
        "salir": "/maquinarias/logout",
        "landing": "https://nopasanadape.com/maquinarias",
    }
    imgs = {
        "logo_nopasanadape": "https://nopasanadape.com/static/images/logo-nopasanadape-transparente-negro.png",
        "logo_maquinarias": "https://nopasanadape.com/static/images/maquinarias-icon.png",
    }
    metadata = {"urls": urls, "imgs": imgs}

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

    return payload


def calculo_plazos(fecha_vigencia, fecha_actualizacion):
    STATUS_BG = {
        "ok": "#d1e7dd",
        "advertencia": "#fff3cd",
        "peligro": "#f8d7da",
        "info": "#cff4fc",
    }
    # calcular dias desde ultima actualizacion
    dias_a = (dt.now() - dt.strptime(fecha_actualizacion, "%Y-%m-%d")).days
    fecha_actualizacion = date_to_user_format(fecha_actualizacion)
    if fecha_actualizacion == "01-Ene-2020":
        fecha_actualizacion = "Pendiente Actualización"
        dias_desde = "N/A"
    else:
        if dias_a > 0:
            dias_desde = f"hace {dias_a:,} {'día' if dias_a == 1 else 'días'}"
        else:
            dias_desde = "hoy"

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

        fecha_vigencia = (
            date_to_user_format(fecha_vigencia) if fecha_vigencia else "N/A"
        )
        dias_restantes = (
            f"{dias_v:,} {'día' if dias_v == 1 else 'días'} " if dias_v >= 0 else ""
        )

        return {
            "estado": estado,
            "estado_bg": estado_bg,
            "vigencia": {
                "fecha": fecha_vigencia,
                "dias_restantes": dias_restantes,
            },
            "ultima_actualizacion": {
                "fecha": fecha_actualizacion,
                "dias_desde": dias_desde,
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
                "fecha": fecha_actualizacion,
                "dias_desde": dias_desde,
            },
        }


def fecha_primera_revtec(ano_fabricacion, placa):
    cronograma = {
        0: "02-28",
        1: "03-31",
        2: "04-30",
        3: "05-31",
        4: "06-30",
        5: "08-31",
        6: "09-30",
        7: "10-31",
        8: "11-30",
        9: "12-31",
    }
    return f"{int(ano_fabricacion) + 4}-{cronograma[int(placa[-1])]}"
