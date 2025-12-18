from datetime import datetime as dt, timedelta as td
from queue import Empty
import time
from func_timeout import exceptions

# local imports
from src.scrapers import scrape_recvehic
from src.utils.webdriver import ChromeUtils
from src.utils.constants import HEADLESS


def gather(
    dash, queue_update_data, local_response, total_original, lock, card, subthread
):

    # construir webdriver con parametros especificos
    chromedriver = ChromeUtils(headless=HEADLESS["revtec"])
    webdriver = chromedriver.direct_driver()

    # iniciar variables para calculo de ETA
    tiempo_inicio = time.perf_counter()
    procesados = 0
    eta = 0

    # iterar hasta vaciar la cola compartida con otras instancias del scraper
    while True:

        # intentar extraer siguiente registro de cola compartida
        try:
            record_item = queue_update_data.get_nowait()
            id_member, doc_tipo, doc_num = record_item
        except Empty:
            dash.log(
                card=card,
                title=f"Record Vehicular-{subthread} [PROCESADOS: {procesados}]",
                status=3,
                text="Inactivo",
                lastUpdate=f"Fin: {dt.strftime(dt.now(),"%H:%M:%S")}",
            )
            break

        # loop to catch scraper errors and retry limited times
        try:
            # registrar inicio en dashboard
            dash.log(
                card=card,
                title=f"Record Vehicular-{subthread} [Pendientes: {total_original-procesados}]",
                status=1,
                text=f"Procesando: {doc_tipo} {doc_num}",
                lastUpdate=f"ETA: {eta}",
            )

            # enviar registro a scraper
            scraper_response = scrape_recvehic.browser_wrapper(
                doc_num=doc_num, webdriver=webdriver, lock=lock
            )
            procesados += 1

            # si respuesta es texto, hubo un error -- regresar
            if isinstance(scraper_response, str) and len(scraper_response) < 100:
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
                    local_response.append(
                        {
                            "Empty": True,
                            "IdMember_FK": id_member,
                        }
                    )
                dash.log(action=f"[ RECVEHIC ] {doc_tipo} {doc_num}")
                continue

            # contruir respuesta
            with lock:
                local_response.append(
                    {
                        "IdMember_FK": id_member,
                        "ImageBytes": scraper_response,
                        "LastUpdate": dt.now().strftime("%Y-%m-%d"),
                    }
                )

            # calcular ETA aproximado
            duracion_promedio = (time.perf_counter() - tiempo_inicio) / procesados
            eta = dt.strftime(
                dt.now()
                + td(seconds=duracion_promedio * (total_original - procesados)),
                "%H:%M:%S",
            )

            dash.log(action=f"[ RECVEHIC ] {doc_tipo} {doc_num}")

        except KeyboardInterrupt:
            quit()

        except exceptions.FunctionTimedOut:
            # devolver registro a la cola para que otro thread lo complete
            if record_item is not None:
                queue_update_data.put(record_item)

            dash.log(
                card=card,
                status=2,
                lastUpdate="ERROR: Timeout",
            )
            break

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
    dash.assigned_cards.remove(card)
    webdriver.quit()
