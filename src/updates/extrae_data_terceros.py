import time
from threading import Thread, Lock
from func_timeout import func_timeout, exceptions
from queue import Queue, Empty
from pprint import pformat
from datetime import datetime as dt
import logging

from src.utils.webdriver import ChromeUtils
from src.scrapers import configuracion_scrapers
from src.utils.utils import date_to_db_format
from src.server import do_updates
from src.utils.constants import TIMEOUT_RECOLECTOR


logger = logging.getLogger(__name__)


def recolector(db, data_actualizar, queue_respuesta, lock, headless):
    """
    Asigna cada registro que necesita ser actualizado al scraper que corresponde en threads.
    Controla el maximo numero de scrapers activados en paralelo.
    Variable "queue_respuesta" junta todas las respuestas de los scrapers
    """
    MAX_SIMULTANEOUS_SCRAPERS = 5
    logger.info(
        f"Iniciando Recolector de Scrapers... maximo simultaneo = {MAX_SIMULTANEOUS_SCRAPERS}. Timeout en {TIMEOUT_RECOLECTOR} segundos"
    )

    # llenar queue con todos los datos por actualizar
    queue_data = Queue()
    for k, item in enumerate(data_actualizar, start=1):
        queue_data.put(item)
    logger.info(f"Cargada cola con data para enviar a scrapers. Total registros = {k}")

    # mantener dentro del loop mientras hayan datos por asignar o queden threads vivos
    active_threads = []
    while queue_data.qsize() > 0 or any(t.is_alive() for t in active_threads):
        # si quedan threads disponibles, asignar siguiente registro
        if sum(t.is_alive() for t in active_threads) < MAX_SIMULTANEOUS_SCRAPERS:
            thread = Thread(
                target=extrae_data_thread,
                args=(db, queue_data, queue_respuesta, lock, headless),
            )
            active_threads.append(thread)
            thread.start()
            logger.debug(f"Iniciado Thread {thread.name}")
            time.sleep(2)
        else:
            time.sleep(1)


def extrae_data_thread(db, queue_data, queue_respuesta, lock, headless):
    """
    Crea una thread individual que llama al scraper que corresponde, envia la data y procesa el resultado.
    Usa los datos de configuracion_scrapers para determinar datos requeridos y modelo de respuesta
    """

    # intentar extraer siguiente registro de cola
    try:
        dato = queue_data.get_nowait()
        logger.debug(f"Obtenido dato de cola: {dato['Categoria']}")

        config = configuracion_scrapers.config(indice=dato["Categoria"])
    except Empty:
        return

    # hay un dato valido, asignar scraper
    chromedriver = ChromeUtils()

    # webdriver residencial o no (datacenter)
    webdriver = chromedriver.proxy_driver(residential=config["residential_proxy"])

    # lanzar scraper dentro de un wrapper para timeout
    try:
        func_scraper = config["funcion_scraper"]
        logger.info(f"Enviado dato a scraper {dato['Categoria']}: Indice: {dato}.")
        if config["api"]:
            respuesta_scraper = func_scraper.api(datos=dato, timeout=config["timeout"])
        else:
            respuesta_scraper = func_timeout(
                config["timeout"],
                func_scraper.browser,
                args=(dato, webdriver, headless),
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
        with lock:
            logger.info(f"Enviado a actualizar base de datos: {respuesta_local}")
            do_updates.main(db, [respuesta_local])

        # regresa al recolector
        time.sleep(1)

    # scraper no termino a tiempo, se devuelve dato a la cola y regresa al recolector
    except exceptions.FunctionTimedOut:
        logger.warning(f"Timeout de scraper {dato['Categoria']}. Indice: {dato}")
        queue_data.put(dato)
        time.sleep(1)

    # error generico - NO devolver el dato a la cola y regresar al recolector
    except Exception as e:
        logger.warning(
            f"Error general de scraper: {dato['Categoria']}. Indice: {dato} \n{e}"
        )
        time.sleep(1)

    finally:
        webdriver.quit()


def main(db, data_actualizar, headless=True):
    """
    Punto de Entrada para Iniciar Proceso de Scraping.
    Controla el timeout general de todo el proceso.
    Al completar el proceso (todos los registros o timeout) actualiza la base de datos.
    Retorna True si se actualizaron todos los registros, False si no se actualizaron todos.
    """

    lock = Lock()
    queue_respuesta = Queue()
    respuesta = []

    try:
        inicio = time.perf_counter()
        func_timeout(
            TIMEOUT_RECOLECTOR,
            recolector,
            args=(db, data_actualizar, queue_respuesta, lock, headless),
        )
        logger.info(
            f"Final normal de Recolector. Tiempo = {time.perf_counter() - inicio}"
        )
        while not queue_respuesta.empty():
            respuesta.append(queue_respuesta.get())

        return respuesta

    except exceptions.FunctionTimedOut:
        logger.warning(f"Timeout de Recolector en {TIMEOUT_RECOLECTOR} s.")
        while not queue_respuesta.empty():
            respuesta.append(queue_respuesta.get())

        return respuesta
