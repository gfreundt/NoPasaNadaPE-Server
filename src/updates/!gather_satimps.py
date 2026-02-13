from datetime import datetime as dt, timedelta as td
import threading
import queue
import time

# local imports
from src.scrapers import scrape_satimp
from src.utils.webdriver import ChromeUtils
from src.utils.constants import HEADLESS, GATHER_ITERATIONS


def manage_sub_threads(dash, lock, update_data, full_response):

    # create variable that accumulates all sub-thread responses
    local_response_codigos, local_response_deudas = [], []

    # load queue with data that needs to be updated
    queue_update_data = queue.Queue()
    for item in update_data:
        queue_update_data.put(item)

    # launch and join N sub-threads for the main thread
    lock = threading.Lock()
    threads = []
    card = 15
    for _ in range(GATHER_ITERATIONS):
        t = threading.Thread(
            target=gather,
            args=(
                dash,
                queue_update_data,
                local_response_codigos,
                local_response_deudas,
                len(update_data),
                lock,
                card,
                card - 15,
            ),
        )
        t.start()
        threads.append(t)
        card += 1
    for t in threads:
        t.join()

    # put all respones into global collector variables
    full_response.update({"DataSatImpuestosCodigos": local_response_codigos})
    full_response.update({"DataSatImpuestosDeudas": local_response_deudas})


def gather(
    dash,
    queue_update_data,
    local_response_codigos,
    local_response_deudas,
    total_original,
    lock,
    card,
    subthread,
):

    # construir webdriver con parametros especificos
    chromedriver = ChromeUtils(headless=HEADLESS["revtec"])
    webdriver = chromedriver.direct_driver()

    # iniciar variables para calculo de ETA
    tiempo_inicio = time.perf_counter()
    procesados = 0
    eta = 0

    # iterate on all records that require updating and get scraper results
    while True:

        # intentar extraer siguiente registro de cola compartida
        try:
            record_item = queue_update_data.get_nowait()
            id_member, doc_tipo, doc_num = record_item
        except queue.Empty:
            # log de salida del scraper
            dash.log(
                card=card,
                title=f"Impuestos SAT-{subthread} [PROCESADOS: {procesados}]",
                status=3,
                text="Inactivo",
                lastUpdate=f"Fin: {dt.strftime(dt.now(),"%H:%M:%S")}",
            )
            break

        # se tiene un registro, intentar extraer la informacion
        try:
            dash.log(
                card=card,
                title=f"Impuestos SAT-{subthread} [Pendientes: {total_original-procesados}]",
                status=1,
                text=f"Procesando: {doc_tipo} {doc_num}",
                lastUpdate=f"ETA: {eta}",
            )

            # send request to scraper
            scraper_response = scrape_satimp.browser_wrapper(
                doc_tipo=doc_tipo, doc_num=doc_num, webdriver=webdriver
            )
            procesados += 1

            # si respuesta es texto, hubo un error -- regresar
            if isinstance(scraper_response, str):
                dash.log(
                    card=card,
                    status=2,
                    lastUpdate=f"ERROR: {scraper_response}",
                )
                # devolver registro a la cola para que otro thread lo complete
                if record_item is not None:
                    queue_update_data.put(record_item)

                # si error permite reinicio ("@") esperar 10 segundos y empezar otra vez
                if "@" in scraper_response:
                    dash.log(
                        card=card,
                        text="Reinicio en 10 segundos",
                        status=1,
                    )
                    time.sleep(10)
                    continue

                # si error no permite reinicio, salir
                break

            # respuesta es en blanco
            if not scraper_response:
                with lock:
                    local_response_codigos.append(
                        {
                            "Empty": True,
                            "IdMember_FK": id_member,
                        }
                    )
                dash.log(action=f"[ SATIMPS ] {doc_tipo} {doc_num}")
                continue

            _now = dt.now().strftime("%Y-%m-%d")

            # contruir respuesta
            for _n in scraper_response:
                with lock:
                    local_response_codigos.append(
                        {
                            "IdMember_FK": id_member,
                            "Codigo": _n["codigo"],
                            "LastUpdate": _now,
                        }
                    )
                if _n["deudas"]:
                    for deuda in _n["deudas"]:
                        local_response_deudas.append(
                            {
                                "Codigo": _n["codigo"],
                                "Ano": deuda[0],
                                "Periodo": deuda[1],
                                "DocNum": deuda[2],
                                "TotalAPagar": deuda[3],
                                "FechaHasta": deuda[4],
                                "LastUpdate": _now,
                            }
                        )
                else:
                    local_response_deudas.append(
                        {
                            "Empty": True,
                            "Codigo": _n["codigo"],
                        }
                    )

            # calcular ETA aproximado
            duracion_promedio = (time.perf_counter() - tiempo_inicio) / procesados
            eta = dt.strftime(
                dt.now()
                + td(seconds=duracion_promedio * (total_original - procesados)),
                "%H:%M:%S",
            )

            dash.log(action=f"[ SATIMPS ] {doc_tipo} {doc_num}")

        except KeyboardInterrupt:
            quit()

        except Exception as e:
            # devolver registro a la cola para que otro thread lo complete
            if record_item is not None:
                queue_update_data.put(record_item)

            # actualizar dashboard
            dash.log(
                card=card,
                text=f"Crash (Gather): {str(e)[:55]}",
                status=2,
            )
            break

    # sacar worker de lista de activos cerrar driver
    webdriver.quit()
