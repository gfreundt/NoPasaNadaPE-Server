from datetime import datetime as dt
import time
from queue import Empty
from func_timeout import exceptions

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_calmul
from src.utils.webdriver import ChromeUtils
from src.utils.constants import HEADLESS


def gather(
    dash, queue_update_data, local_response, total_original, lock, card, subthread
):

    # construir webdriver con parametros especificos
    chromedriver = ChromeUtils(headless=HEADLESS["calmul"])
    webdriver = chromedriver.direct_driver()

    # iniciar variables para calculo de ETA
    procesados = 0

    # iterar hasta vaciar la cola compartida con otras instancias del scraper
    while True:

        # intentar extraer siguiente registro de cola compartida
        try:
            record_item = queue_update_data.get_nowait()
            placa = record_item
        except Empty:
            dash.log(
                card=card,
                status=3,
                title=f"Multas Callao-{subthread} [PROCESADOS: {procesados}]",
                text="Inactivo",
                lastUpdate=f"Fin: {dt.strftime(dt.now(),"%H:%M:%S")}",
            )
            break

        # se tiene un registro, intentar extraer la informacion
        try:
            # actualizar dashboard con registro en proceso
            dash.log(
                card=card,
                title=f"Multas Callao-{subthread} [Pendientes: {total_original-procesados}]",
                text=f"Procesando: {placa}",
                status=1,
            )

            # enviar registro a scraper
            scraper_response = scrape_calmul.browser_wrapper(
                placa=placa, webdriver=webdriver
            )

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
                        status=2,
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
                            "PlacaValidate": placa,
                        }
                    )
                # texto en dashboard
                dash.log(action=f"[ CALMUL ] {placa}")
                continue

            # ajustar formato de fechas al de la base de datos (YYYY-MM-DD)
            _n = date_to_db_format(data=scraper_response)

            # agregar registo a acumulador de respuestas (compartido con otros scrapers)
            local_response.append(
                {
                    "PlacaValidate": placa,
                    "Codigo": _n[0],
                    "NumeroPapeleta": _n[1],
                    "FechaInfraccion": _n[2],
                    "TotalInfraccion": _n[3],
                    "TotalBeneficio": _n[4],
                    "ImageBytes": _n[5],
                    "LastUpdate": dt.now().strftime("%Y-%m-%d"),
                }
            )

            # calcular ETA aproximado
            procesados += 1

            # texto en dashboard
            dash.log(action=f"[ BREVETES ] {placa}")

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
