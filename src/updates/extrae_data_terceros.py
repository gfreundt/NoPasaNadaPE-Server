import time
from threading import Thread, Lock
from func_timeout import func_timeout
from func_timeout.exceptions import FunctionTimedOut
from queue import Queue
from src.updates import extrae_data_terceros_individual


from src.utils.constants import TIMEOUT_RECOLECTOR
import logging

logger = logging.getLogger(__name__)


def recolector(db, data_actualizar, queue_respuesta, lock):
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
                target=extrae_data_terceros_individual.main,
                args=(db, queue_data, queue_respuesta, lock),
            )
            active_threads.append(thread)
            thread.start()
            logger.debug(f"Iniciado Thread {thread.name}")
            time.sleep(2)
        else:
            time.sleep(1)


def main(db, data_actualizar):
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
            args=(db, data_actualizar, queue_respuesta, lock),
        )
        logger.info(
            f"Final normal de Recolector. Tiempo = {time.perf_counter() - inicio}"
        )
        while not queue_respuesta.empty():
            respuesta.append(queue_respuesta.get())

        return respuesta

    except FunctionTimedOut:
        logger.warning(f"Timeout de Recolector en {TIMEOUT_RECOLECTOR} s.")
        while not queue_respuesta.empty():
            respuesta.append(queue_respuesta.get())

        return respuesta
