from func_timeout import func_timeout
from func_timeout.exceptions import FunctionTimedOut
from queue import Empty
from pprint import pformat
from src.utils.webdriver import ChromeUtils
from src.scrapers import configuracion_scrapers
from src.utils.utils import date_to_db_format
from datetime import datetime as dt

import logging

logger = logging.getLogger(__name__)


def main(queue_data, queue_respuesta):
    # intentar extraer siguiente registro de cola
    try:
        dato = queue_data.get_nowait()
        logger.debug(f"Obtenido dato de cola: {dato['Categoria']}")

        if dato["Categoria"] != "DataCallaoMultas":
            return

        config = configuracion_scrapers.config(indice=dato["Categoria"])
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

    # lanzar scraper dentro de un wrapper para timeout
    try:
        func_scraper = config["funcion_scraper"]
        logger.info(
            f"Enviado dato a scraper {dato['Categoria']}: Indice: {datos_scraper}."
        )
        respuesta_scraper = func_timeout(
            config["timeout"], func_scraper.browser, args=(datos_scraper, webdriver)
        )
        logger.debug(f"Respuesta scraper: {pformat(respuesta_scraper)}")

        # si respuesta es texto, hubo un error -- reponer dato a cola y vuelve sin actualizar acumulador
        if isinstance(respuesta_scraper, str):
            queue_data.put(dato)
            logger.warning(f"Error de scraper: {respuesta_scraper}")
            return

        # respuesta es valida - armar esqueleto de respuesta scraper
        respuesta_local = {
            "Categoria": dato["Categoria"],
            "Placa": dato.get("Placa"),
            "IdMember": dato.get("IdMember"),
            "LastUpdate": dt.now().strftime("%Y-%m-%d"),
        }

        payload = []

        # en caso respuesta tenga data - armar payload como lista de respuestas de scraper
        for item in respuesta_scraper:
            item_formateado = date_to_db_format(item)
            parte_payload = {
                key: item_formateado[pos] if pos is not None else ""
                for key, pos in config["estructura_respuesta"].items()
            }
            payload.append(parte_payload)
            logger.debug(f"Agregado a Payload: {parte_payload}")

        # actualiza respuesta base con payload (vacio o con datos) y agrega al acumulador
        respuesta_local.update({"Payload": payload})
        queue_respuesta.put(respuesta_local)
        logger.info(f"Resultado de Armado de Data Post-Scraper: {respuesta_local}")

        # cierra webdriver y regresa al recolector
        webdriver.quit()

    # scraper no termino a tiempo, se devuelve dato a la cola y regresa al recolector
    except FunctionTimedOut:
        logger.warning("Timeout de scraper.")
        queue_data.put(dato)

    # error generico - devolver el dato a la cola y regresar al recolector
    except Exception as e:
        logger.warning(f"Error general de scraper: {e}")
        queue_data.put(dato)
