from func_timeout import func_timeout
from func_timeout.exceptions import FunctionTimedOut
from queue import Empty
import time
from src.utils.webdriver import ChromeUtils

from src.utils.utils import date_to_db_format
from datetime import datetime as dt
from src.scrapers import (
    scrape_brevete,
    scrape_revtec,
    scrape_sutran,
    scrape_satimp,
    scrape_recvehic,
    scrape_sunarp,
    scrape_satmul,
    scrape_soat,
    scrape_calmul,
)

import random, string


def main(queue_data, respuesta_acumulada, lock):
    # intentar extraer siguiente registro de cola
    try:
        dato = queue_data.get_nowait()
        if dato["Categoria"] != "DataMtcBrevetes":
            return
        config = scraper_config(indice=dato["Categoria"])
        print(dato)
        print("------------")
    except Empty:
        return

    # hay un dato valido, asignar scraper
    chromedriver = ChromeUtils()

    # webdriver residencial o no (datacenter)
    webdriver = chromedriver.proxy_driver(residential=config["residential_proxy"])

    # definir datos necesarios para el scraper
    if config["indice_placa"]:
        datos_scraper = dato["Placa"]
    else:
        datos_scraper = (dato["DocTipo"], dato["DocNum"])

    # enviar a wrapper para controlar timeout
    try:
        func_scraper = config["funcion_scraper"]
        # respuesta_scraper = func_timeout(
        #     config["timeout"], fake_scraper, args=(datos_scraper, webdriver)
        # )
        respuesta_scraper = func_timeout(
            config["timeout"], func_scraper.browser, args=(datos_scraper, webdriver)
        )

        print("/////////")
        print(respuesta_scraper)
        print("/////////")

        # si respuesta es texto, hubo un error -- reponer dato a cola y vuelve sin actualizar acumulador
        if isinstance(respuesta_scraper, str):
            # queue_data.put(dato)
            return

        # respuesta es valida - armar esqueleto de respuesta scraper
        respuesta_local = {
            "Categoria": dato["Categoria"],
            "Placa": dato.get("Placa"),
            "IdMember": dato.get("IdMember"),
        }

        payload = []

        # en caso respuesta tenga data - armar payload como lista de respuestas de scraper
        for item in respuesta_scraper:
            _r = item
            # print(_r)
            # print(config["estructura_respuesta"])
            # _r = date_to_db_format(data=item)
            parte_payload = {
                key: _r[pos] if pos is not None else ""
                for key, pos in config["estructura_respuesta"].items()
            }
            payload.append(post_procesamiento(parte_payload))

        # actualiza respuesta base con payload (vacio o con datos) y agrega al acumulador
        respuesta_local.update({"Payload": payload})
        with lock:
            respuesta_acumulada.append(respuesta_local)

        # cierra webdriver y regresa al recolector
        webdriver.quit()

    # scraper no termino a tiempo, se devuelve dato a la cola y regresa al recolector
    except FunctionTimedOut:
        print("Timeout One...")
        queue_data.put(dato)

    # error generico - devolver el dato a la cola y regresar al recolector
    # except Exception as e:
    #     print(e)
    # queue_data.put(dato)


def fake_scraper(datos_scraper, webdriver):
    time.sleep(random.randrange(5, 35))
    return [
        [
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 120)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 440)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 955499)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 333)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 111)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
            "".join(random.choices(string.ascii_uppercase, k=3))
            + str(random.randint(100, 999)),
        ]
    ]


def armar_payload(r, e):
    payload = {}
    for key, pos in e.items():
        payload[key] = r[pos] if pos is not None else ""
    payload["LastUpdate"] = (dt.now().strftime("%Y-%m-%d"),)

    payload = {key: r[pos] if pos else "" for key, pos in e.items()}


def post_procesamiento(payload):
    """
    Agrega detalles al payload que son especificos de cada tipo de scraper
    """

    # SOAT imagen certificado

    return payload


def scraper_config(indice):
    todo = {
        "DataMtcRecordsConductores": {
            "residential_proxy": False,
            "indice_placa": False,
            "funcion_scraper": scrape_recvehic,
            "timeout": 60,
            "estructura_respuesta": {
                "ImageBytes": 0,
            },
        },
        "DataMtcBrevetes": {
            "residential_proxy": True,
            "indice_placa": False,
            "funcion_scraper": scrape_brevete,
            "timeout": 90,
            "estructura_respuesta": {
                "Clase": 0,
                "Numero": 1,
                "Tipo": 2,
                "FechaExp": 3,
                "Restricciones": 4,
                "FechaHasta": 5,
                "Centro": 6,
                "Puntos": 7,
                "Record": 8,
            },
        },
        "DataSatMultas": {
            "residential_proxy": False,
            "indice_placa": True,
            "funcion_scraper": scrape_satmul,
            "timeout": 300,
            "estructura_respuesta": {
                "IdPlaca_FK": None,
                "PlacaValidate": 0,
                "Reglamento": 1,
                "Falta": 2,
                "Documento": 3,
                "FechaEmision": 4,
                "Importe": 5,
                "Gastos": 6,
                "Descuento": 7,
                "Deuda": 8,
                "Estado": 9,
                "Licencia": 10,
                "DocTipoSatmul": 11,
                "DocNumSatmul": 12,
                "ImageBytes1": 13,
                "ImageBytes2": 14,  # forzar que scraper devuelva el 14 en blanco
            },
        },
        "DataSatImpuestos": {
            "residential_proxy": False,
            "indice_placa": False,
            "funcion_scraper": scrape_satimp,
            "timeout": 60,
        },
        "DataMtcRevisionesTecnicas": {
            "residential_proxy": True,
            "indice_placa": True,
            "funcion_scraper": scrape_revtec,
            "timeout": 60,
            "estructura_respuesta": {
                "IdPlaca_FK": None,
                "Certificadora": 0,
                "PlacaValidate": 2,
                "Certificado": 3,
                "FechaDesde": 4,
                "FechaHasta": 5,
                "Resultado": 6,
                "Vigencia": 7,
            },
        },
        "DataSutranMultas": {
            "residential_proxy": False,
            "indice_placa": True,
            "funcion_scraper": scrape_sutran,
            "timeout": 60,
            "estructura_respuesta": {
                "Documento": 0,
                "Tipo": 1,
                "FechaDoc": 2,
                "CodigoInfrac": 3,
                "Clasificacion": 4,
            },
        },
        "DataSunarpFichas": {
            "residential_proxy": True,
            "indice_placa": True,
            "funcion_scraper": scrape_sunarp,
            "timeout": 90,
        },
        "DataApesegSoats": {
            "residential_proxy": False,
            "indice_placa": True,
            "funcion_scraper": scrape_soat,
            "timeout": 60,
            "estructura_respuesta": {
                "IdPlaca_FK": None,
                "Aseguradora": 0,
                "Vigencia": 1,
                "FechaInicio": 2,
                "FechaHasta": 3,
                "PlacaValidate": 4,
                "Certificado": 5,
                "Uso": 6,
                "Clase": 7,
                "Tipo": 8,
                "FechaVenta": 9,
                "ImageBytes": None,
            },
        },
        "DataCallaoMultas": {
            "residential_proxy": False,
            "indice_placa": True,
            "funcion_scraper": scrape_calmul,
            "timeout": 45,
            "estructura_respuesta": {
                "PlacaValidate": 0,
                "Codigo": 1,
                "NumeroPapeleta": 2,
                "FechaInfraccion": 3,
                "TotalInfraccion": 4,
                "TotalBeneficio": 5,
                "ImageBytes": None,
            },
        },
    }

    return todo[indice]
