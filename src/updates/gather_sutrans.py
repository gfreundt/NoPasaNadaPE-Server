from datetime import datetime as dt, timedelta as td
from queue import Empty
import time

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_sutran
from src.utils.webdriver import ChromeUtils
from src.utils.constants import HEADLESS


def gather(
    dash, queue_update_data, local_response, total_original, lock, card, subthread
):

    # construir webdriver con parametros especificos
    chromedriver = ChromeUtils(headless=HEADLESS["revtec"])
    webdriver = chromedriver.direct_driver()

    # registrar inicio en dashboard

    # iniciar variables para calculo de ETA
    tiempo_inicio = time.perf_counter()
    procesados = 0
    eta = 0

    # iterar hasta vaciar la cola compartida con otras instancias del scraper
    while True:

        # grab next record from update queue unless empty
        try:
            record_item = queue_update_data.get_nowait()
            placa = record_item
        except Empty:
            # log de salida del scraper
            dash.log(
                card=card,
                title=f"Sutran-{subthread} [PROCESADOS: {procesados}]",
                status=3,
                text="Inactivo",
                lastUpdate=f"Fin: {dt.strftime(dt.now(),"%H:%M:%S")}",
            )
            break

        # loop to catch scraper errors and retry limited times
        try:
            dash.log(
                card=card,
                title=f"Sutran-{subthread} [Pendientes: {total_original-procesados}]",
                status=1,
                text=f"Procesando: {placa}",
                lastUpdate=f"ETA: {eta}",
            )

            # send request to scraper
            scraper_response = scrape_sutran.browser_wrapper(placa, webdriver)
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
                    local_response.append(
                        {
                            "Empty": True,
                            "PlacaValidate": placa,
                        }
                    )
                dash.log(action=f"[ SUTRANS ] {placa}")
                continue

            # iterate on all multas
            for resp in scraper_response:
                _n = date_to_db_format(data=resp)
                with lock:
                    local_response.append(
                        {
                            "PlacaValidate": placa,
                            "Documento": _n[0],
                            "Tipo": _n[1],
                            "FechaDoc": _n[2],
                            "CodigoInfrac": _n[3],
                            "Clasificacion": _n[4],
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

            dash.log(action=f"[ SUTRANS ] {placa}")

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
    dash.assigned_cards.remove(card)
    webdriver.quit()
