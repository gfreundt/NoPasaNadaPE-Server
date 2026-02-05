import time
import os
import json
from threading import Thread
from func_timeout import func_timeout
from func_timeout.exceptions import FunctionTimedOut
from queue import Queue
from src.server import do_updates
from src.updates import gather_one
from src.utils.constants import NETWORK_PATH
import logging

logger = logging.getLogger(__name__)


def recolector(data_actualizar, queue_respuesta):
    """
    Asigna cada registro que necesita ser actualizado al scraper que corresponde en threads.
    Controla el maximo numero de scrapers activados en paralelo.
    Variable "queue_respuesta" junta todas las respuestas de los scrapers
    """
    MAX_SIMULTANEOUS_SCRAPERS = 3
    logger.info(
        f"Iniciando Recolector de Scrapers... maximo simulataneo = {MAX_SIMULTANEOUS_SCRAPERS}"
    )

    # llenar queue con todos los datos por actualizad
    queue_data = Queue()
    for k, item in enumerate(data_actualizar):
        queue_data.put(item)
    logger.info(f"Cargada cola con data para enviar a scrapers. Total registros = {k}")

    # mantener dentro del loop mientras hayan datos por asignar o queden threads vivos
    active_threads = []
    while queue_data.qsize() > 0 or any(t.is_alive() for t in active_threads):
        # si quedan threads disponibles, asignar siguiente registro
        if sum(t.is_alive() for t in active_threads) < MAX_SIMULTANEOUS_SCRAPERS:
            thread = Thread(
                target=gather_one.main,
                args=(queue_data, queue_respuesta),
            )
            active_threads.append(thread)
            thread.start()
            logger.debug(f"Iniciado Thread {thread.name}")
            time.sleep(2)
        else:
            time.sleep(1)


def grabar_datos(self, queue_respuesta):
    """
    Graba los datos en la base de datos y/o en un archivo local
    """

    # vacear cola en lista
    respuesta = []
    while not queue_respuesta.empty():
        respuesta.append(queue_respuesta.get())

    # intenta actualizar base de datos
    exito = do_updates.main(self, data=respuesta)

    # actualizacion correcta, fin de proceso
    if exito:
        logger.info(f"Base de datos actualizada. Total registros = {len(respuesta)}")
        return

    # si no se pudo actualizar base de datos grabar en archivo local
    update_files = [
        int(i[-10:-5])
        for i in os.listdir(os.path.join(NETWORK_PATH, "security"))
        if "update_" in i
    ]

    next_secuential = max(update_files) + 1 if update_files else 0
    path = os.path.join(NETWORK_PATH, "security", f"update_{next_secuential:05d}.json")
    with open(path, mode="w") as outfile:
        outfile.write(json.dumps(respuesta))
    logger.warning(
        f"No se pudo grabar data de scrapers a base de datos. Grabado localmente a {path}. Total registros = {len(respuesta)}"
    )


def main(self, data_actualizar):
    """
    Punto de Entrada para Iniciar Proceso de Scraping.
    Controla el timeout general de todo el proceso.
    Al completar el proceso (todos los registros o timeout) actualiza la base de datos.
    Retorna True si se actualizaron todos los registros, False si no se actualizaron todos.
    """
    data_actualizar = get_sample_data()
    print("DATA BAMBA!!")

    TIMEOUT = 240
    queue_respuesta = Queue()

    try:
        inicio = time.perf_counter()
        func_timeout(TIMEOUT, recolector, args=(data_actualizar, queue_respuesta))
        logger.info(
            f"Final normal de Recolector. Tiempo = {time.perf_counter() - inicio}"
        )
        exito = True

    except FunctionTimedOut:
        logger.warrning(f"Timeout de Recolector en {TIMEOUT} s.")
        exito = False

    finally:
        grabar_datos(self, queue_respuesta)

    return exito


def get_sample_data():
    return [
        {
            "Categoria": "DataApesegSoats",
            "IdMember": 29,
            "Placa": "F2L100",
            "DocTipo": "DNI",
            "DocNum": "91387786",
        },
        {
            "Categoria": "DataCallaoMultas",
            "IdMember": 71,
            "Placa": "CRN409",
            "DocTipo": "DNI",
            "DocNum": "74671955",
        },
        {
            "Categoria": "DataSatImpuestos",
            "IdMember": 29,
            "Placa": "F2L100",
            "DocTipo": "DNI",
            "DocNum": "91387786",
        },
        {
            "Categoria": "DataMtcRecordsConductores",
            "IdMember": 36,
            "Placa": "FTR814",
            "DocTipo": "DNI",
            "DocNum": "72773304",
        },
        {
            "Categoria": "DataSutranMultas",
            "IdMember": 8,
            "Placa": "CBW475",
            "DocTipo": "DNI",
            "DocNum": "10541965",
        },
        {
            "Categoria": "DataCallaoMultas",
            "IdMember": 36,
            "Placa": "FTR814",
            "DocTipo": "DNI",
            "DocNum": "72773304",
        },
        {
            "Categoria": "DataCallaoMultas",
            "IdMember": 8,
            "Placa": "CBW475",
            "DocTipo": "DNI",
            "DocNum": "10541965",
        },
        {
            "Categoria": "DataMtcRevisionesTecnicas",
            "IdMember": 36,
            "Placa": "AZT556",
            "DocTipo": "DNI",
            "DocNum": "72773304",
        },
        {
            "Categoria": "DataMtcRevisionesTecnicas",
            "IdMember": 36,
            "Placa": "CBW475",
            "DocTipo": "DNI",
            "DocNum": "72773304",
        },
        {
            "Categoria": "DataApesegSoats",
            "IdMember": 109,
            "Placa": "CHO571",
            "DocTipo": "DNI",
            "DocNum": "78296819",
        },
        {
            "Categoria": "DataCallaoMultas",
            "IdMember": 23,
            "Placa": "CRN407",
            "DocTipo": "DNI",
            "DocNum": "88045216",
        },
        {
            "Categoria": "DataSatMultas",
            "IdMember": 140,
            "Placa": "CHS662",
            "DocTipo": "DNI",
            "DocNum": "15450767",
        },
        {
            "Categoria": "DataMtcBrevetes",
            "IdMember": 65,
            "Placa": None,
            "DocTipo": "DNI",
            "DocNum": "72773304",
        },
        {
            "Categoria": "DataMtcRecordsConductores",
            "IdMember": 91,
            "Placa": "ZBW-610",
            "DocTipo": "DNI",
            "DocNum": "90573628",
        },
        {
            "Categoria": "DataSatMultasXX",
            "IdMember": 77,
            "Placa": "ALM239",
            "DocTipo": "DNI",
            "DocNum": "10059261",
        },
        {
            "Categoria": "DataSatImpuestos",
            "IdMember": 71,
            "Placa": "AVN061",
            "DocTipo": "DNI",
            "DocNum": "74671955",
        },
        {
            "Categoria": "DataCallaoMultas",
            "IdMember": 148,
            "Placa": "AVN061",
            "DocTipo": "DNI",
            "DocNum": "86617420",
        },
        {
            "Categoria": "DataMtcBrevetes",
            "IdMember": 8,
            "Placa": None,
            "DocTipo": "DNI",
            "DocNum": "10541965",
        },
        {
            "Categoria": "DataSutranMultas",
            "IdMember": 148,
            "Placa": "AYN334",
            "DocTipo": "DNI",
            "DocNum": "86617420",
        },
    ]
