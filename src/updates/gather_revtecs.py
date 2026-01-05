from datetime import datetime as dt, timedelta as td
import time
from queue import Empty

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_revtec
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
            placa = record_item
        except Empty:
            # log de salida del scraper
            dash.log(
                card=card,
                title=f"Revisión Técnica ({subthread})",
                status=3,
                text="Inactivo",
                lastUpdate=f"Fin: {dt.strftime(dt.now(),"%H:%M:%S")}",
            )
            break

        # se tiene un registro, intentar extraer la informacion
        try:
            # registrar inicio en dashboard
            dash.log(
                card=card,
                title=f"Revisión Técnica ({subthread}) [Pendientes: {total_original-procesados}]",
                status=1,
                lastUpdate=f"ETA: {eta}",
            )

            # enviar registro a scraper
            scraper_response = scrape_revtec.browser_wrapper(
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
                dash.log(action=f"[ REVTECS ] {placa}")
                continue

            # ajustar formato de fechas al de la base de datos (YYYY-MM-DD)
            _n = date_to_db_format(data=scraper_response)

            # agregar registo a acumulador de respuestas (compartido con otros scrapers)
            with lock:
                local_response.append(
                    {
                        "IdPlaca_FK": 999,
                        "Certificadora": _n[0],
                        "PlacaValidate": _n[2],
                        "Certificado": _n[3],
                        "FechaDesde": _n[4],
                        "FechaHasta": _n[5],
                        "Resultado": _n[6],
                        "Vigencia": _n[7],
                        "LastUpdate": dt.now().strftime("%Y-%m-%d"),
                    }
                )

            # calcular ETA aproximado
            procesados += 1
            duracion_promedio = (time.perf_counter() - tiempo_inicio) / procesados
            eta = dt.strftime(
                dt.now()
                + td(seconds=duracion_promedio * (total_original - procesados)),
                "%H:%M:%S",
            )

            dash.log(action=f"[ REVTECS ] {placa}")

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
