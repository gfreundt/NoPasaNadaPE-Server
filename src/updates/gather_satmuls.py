from datetime import datetime as dt, timedelta as td
import time
from queue import Empty
from func_timeout import exceptions

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_satmul
from src.utils.webdriver import ChromeUtils
from src.utils.constants import HEADLESS


def gather(
    dash, queue_update_data, local_response, total_original, lock, card, subthread
):

    # construir webdriver con parametros especificos
    chromedriver = ChromeUtils(
        headless=HEADLESS["satmul"],
        incognito=True,
        window_size=(1920, 1080),
    )
    # webdriver = chromedriver.direct_driver()
    webdriver = chromedriver.direct_driver()

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
                title=f"Multas SAT-{subthread} [PROCESADOS: {procesados}]",
                status=3,
                text="Inactivo",
                lastUpdate=f"Fin: {dt.strftime(dt.now(),"%H:%M:%S")}",
            )
            break

        # loop to catch scraper errors and retry limited times
        try:
            dash.log(
                card=card,
                title=f"Multas SAT-{subthread} [Pendientes: {total_original-procesados}]",
                status=1,
                text=f"Procesando: {placa}",
                lastUpdate=f"ETA: {eta}",
            )

            # send request to scraper
            scraper_response = scrape_satmul.browser_wrapper(placa, webdriver)
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
                dash.log(action=f"[ SATMULS ] {placa}")
                continue

            # if there is data in response, enter into database, go to next placa
            for resp in scraper_response:

                # adjust date to match db format (YYYY-MM-DD)
                _n = date_to_db_format(data=resp)
                local_response.append(
                    {
                        "IdPlaca_FK": 999,
                        "PlacaValidate": _n[0],
                        "Reglamento": _n[1],
                        "Falta": _n[2],
                        "Documento": _n[3],
                        "FechaEmision": _n[4],
                        "Importe": _n[5],
                        "Gastos": _n[6],
                        "Descuento": _n[7],
                        "Deuda": _n[8],
                        "Estado": _n[9],
                        "Licencia": _n[10],
                        "DocTipoSatmul": _n[11],
                        "DocNumSatmul": _n[12],
                        "ImageBytes1": _n[13],
                        "ImageBytes2": _n[14] if len(_n) > 14 else "",
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

            dash.log(action=f"[ SATMULS ] {placa}")

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
