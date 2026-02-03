from datetime import datetime as dt
import time
import random
import threading
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="seleniumwire")

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Log format
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%H:%M:%S"
)
console_handler.setFormatter(formatter)

# Avoid duplicate handlers if reloaded
if not logger.handlers:
    logger.addHandler(console_handler)

from func_timeout.exceptions import FunctionTimedOut
from src.test.test_data import get_test_data
from src.scrapers import (
    scrape_brevete,
    scrape_calmul,
    scrape_satimp,
    scrape_satmul,
    scrape_soat,
    scrape_recvehic,
    scrape_revtec,
    scrape_sutran,
)
from src.utils.utils import date_to_db_format
from src.utils.webdriver import ChromeUtils


def get_config():
    return {
        "DataMtcBrevetes": {
            "residential": True,
            "llave": "doc",
            "timeout": True,
            "function": scrape_brevete.browser_wrapper,
            "respuesta": {
                "IdMember_FK": None,
                "Clase": 0,
                "Numero": 1,
                "Tipo": 2,
                "FechaExp": 3,
                "Restricciones": 4,
                "FechaHasta": 5,
                "Centro": 6,
                "Puntos": 7,
                "Record": 8,
                "LastUpdate": None,
            },
        },
        "DataCallaoMultas": {
            "residential": False,
            "llave": "placa",
            "function": scrape_calmul.browser_wrapper,
            "timeout": True,
            "respuesta": {
                "PlacaValidate": None,
                "Codigo": 1,
                "NumeroPapeleta": 2,
                "FechaInfraccion": 3,
                "TotalInfraccion": 4,
                "TotalBeneficio": 5,
                "ImageBytes": None,
                "LastUpdate": None,
            },
        },
        "DataMtcRevisionesTecnicas": {
            "residential": True,
            "llave": "placa",
            "function": scrape_revtec.browser_wrapper,
            "timeout": True,
            "respuesta": {
                "IdPlaca_FK": None,
                "Certificadora": 0,
                "PlacaValidate": 2,
                "Certificado": 3,
                "FechaDesde": 4,
                "FechaHasta": 5,
                "Resultado": 6,
                "Vigencia": 7,
                "LastUpdate": None,
            },
        },
        "DataSatMultas": {
            "residential": False,
            "llave": "placa",
            "function": scrape_satmul.browser_wrapper,
            "timeout": True,
            "respuesta": {
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
                "ImageBytes2": 14,
                "LastUpdate": None,
            },
        },
        "DataSutranMultas": {
            "residential": False,
            "llave": "placa",
            "function": scrape_sutran.browser_wrapper,
            "timeout": True,
            "respuesta": {
                "PlacaValidate": None,
                "Documento": 0,
                "Tipo": 1,
                "FechaDoc": 2,
                "CodigoInfrac": 3,
                "Clasificacion": 4,
                "LastUpdate": None,
            },
        },
        "DataApesegSoats": {
            "residential": False,
            "llave": "placa",
            "function": scrape_soat.browser_wrapper,
            "timeout": True,
            "respuesta": {
                "IdPlaca_FK": None,
                "Aseguradora": 0,
                "FechaInicio": 2,
                "FechaHasta": 3,
                "PlacaValidate": 4,
                "Certificado": 5,
                "Uso": 6,
                "Clase": 7,
                "Vigencia": 1,
                "Tipo": 8,
                "FechaVenta": 9,
                "ImageBytes": None,
                "LastUpdate": None,
            },
        },
        "DataMtcRecordsConductores": {
            "residential": True,
            "llave": "doc",
            "function": scrape_recvehic.browser_wrapper,
            "timeout": True,
            "respuesta": {
                "IdMember_FK": None,
                "ImageBytes": 0,
                "LastUpdate": None,
            },
        },
    }


def gather(dato, config):
    # construir webdriver con parametros especificos
    chromedriver = ChromeUtils()

    try:
        webdriver = chromedriver.proxy_driver(residential=config["residential"])
        scraper_response = config["function"](dato, webdriver=webdriver)

        # si respuesta es texto, hubo un error -- regresar
        if isinstance(scraper_response, str):
            return False, scraper_response

        # respuesta es en blanco
        if not scraper_response:
            return True, None

        # ajustar formato de fechas al de la base de datos (YYYY-MM-DD)
        _n = date_to_db_format(data=scraper_response)

        # intentar asignar valores a estructura de respuesta
        return True, None
        respuesta = {i: _n[j] if j else None for i, j in config["respuesta"].items()}

    except Exception as e:
        return False, e

    except FunctionTimedOut:
        logger.warning("⏱ Scraper timed out")
        return False, "Timeout"


def each_thread(scraper, config, data_pruebas):
    logger.debug(f"Iniciando pruebas para scraper manual: {scraper}")
    for dato in data_pruebas[scraper]:
        if type(dato) is list:
            dato = dato[-1]
        start_time = time.perf_counter()
        success, error = gather(dato, config)
        end_time = time.perf_counter()
        if success:
            tiempo = f"{end_time - start_time:.2f}"
            logger.info(f"✅ Scraper: {scraper}. Tiempo: {tiempo} seconds")
            return 1
        else:
            tiempo = "N/A"
            logger.info(f"❌ Scraper: {scraper}. Fallo: {str(error)[:100]}...")
            return 0


def main():
    configuracion = get_config()
    logger.info(
        f"Iniciando pruebas de scrapers en parelelo (Total:{len(configuracion)})."
    )
    data_pruebas = get_test_data(sample_size=1)

    resultados = []
    # threads = []
    for scraper, config in random.sample(
        list(configuracion.items()), len(configuracion)
    ):
        resultado = each_thread(scraper, config, data_pruebas)
        resultados.append(resultado)
    #     thread = threading.Thread(
    #         target=each_thread, args=(scraper, config, data_pruebas)
    #     )
    #     thread.start()
    #     threads.append(thread)

    # for thread in threads:
    #     thread.join()

    txt = f"Prueba de scrapers completa (Total: {len(configuracion)}). Exitos: {sum(resultados)}. Fallos: {len(configuracion) - sum(resultados)}."
    logger.info(txt)

    # activity = send_pushbullet(
    #     title="Prueba de scrapers " + str(dt.now())[:10],
    #     message=txt,
    # )
    # logger.info(f"Pushbullet Resultado Prueba Scrapers Enviado: {activity}")
