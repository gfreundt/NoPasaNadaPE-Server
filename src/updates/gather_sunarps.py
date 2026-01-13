from datetime import datetime as dt, timedelta as td
from queue import Empty
import time

# local imports
from src.scrapers import scrape_sunarp
from src.utils.constants import HEADLESS
from src.utils.webdriver import ChromeUtils
from seleniumbase import SB


def gather(
    dash, queue_update_data, local_response, total_original, lock, card, subthread
):

    # construir webdriver con parametros especificos
    chromedriver = ChromeUtils(
        headless=False,  # HEADLESS["sunarp"],
        incognito=True,
        window_size=(1920, 1080),
    )
    # webdriver = chromedriver.direct_driver()
    webdriver = chromedriver.proxy_driver()

    # iniciar variables para calculo de ETA
    tiempo_inicio = time.perf_counter()
    procesados = 0
    eta = 0

    # iterate on all records that require updating and get scraper results
    while True:

        # intentar extraer siguiente registro de cola compartida
        try:
            record_item = queue_update_data.get_nowait()
            placa = record_item

            # # ---------- EMERGENCIA > SOLO MIENTRAS DURE CAPTCHA
            # with lock:
            #     local_response.append(
            #         {
            #             "Empty": True,
            #             "PlacaValidate": placa,
            #         }
            #     )
            #     dash.log(action=f"[ SUNARPS ] {placa}")
            #     continue

        except Empty:
            # log de salida del scraper
            dash.log(
                card=card,
                status=3,
                title=f"SUNARPS-{subthread} [PROCESADOS: {procesados}]",
                text="Inactivo",
                lastUpdate=f"Fin: {dt.strftime(dt.now(),"%H:%M:%S")}",
            )
            break

        try:
            # log action
            dash.log(
                card=card,
                title=f"SUNARPS-{subthread} [Pendientes: {total_original}]",
                status=1,
                text=f"Procesando: {placa}",
                lastUpdate=f"ETA: {eta}",
            )

            # send request to scraper
            scraper_response = scrape_sunarp.browser_wrapper(
                placa=placa, webdriver=webdriver
            )
            procesados += 1

            # si respuesta es texto, hubo un error -- regresar
            if isinstance(scraper_response, str) and len(scraper_response) < 100:
                dash.log(card=card, status=2, lastUpdate=f"ERROR: {scraper_response}")
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
                dash.log(action=f"[ SUNARPS ] {placa}")
                continue

            _now = dt.now().strftime("%Y-%m-%d")

            # add foreign key and current date to response
            with lock:
                local_response.append(
                    {
                        "IdPlaca_FK": 999,
                        "PlacaValidate": placa,
                        "Serie": "",
                        "VIN": "",
                        "Motor": "",
                        "Color": "",
                        "Marca": "",
                        "Modelo": "",
                        "Ano": "",
                        "PlacaVigente": "",
                        "PlacaAnterior": "",
                        "Estado": "",
                        "Anotaciones": "",
                        "Sede": "",
                        "Propietarios": "",
                        "ImageBytes": scraper_response,
                        "LastUpdate": _now,
                    }
                )

            # calcular ETA aproximado
            duracion_promedio = (time.perf_counter() - tiempo_inicio) / procesados
            eta = dt.strftime(
                dt.now()
                + td(seconds=duracion_promedio * (total_original - procesados)),
                "%H:%M:%S",
            )

            dash.log(action=f"[ SUNARPS ] {placa}")

        except KeyboardInterrupt:
            quit()

        # except Exception as e:
        #     # devolver registro a la cola para que otro thread lo complete
        #     if record_item is not None:
        #         queue_update_data.put(record_item)

        #     # actualizar dashboard
        #     dash.log(
        #         card=card,
        #         text=f"Crash (Gather): {str(e)[:55]}",
        #         status=2,
        #     )
        #     break

    # sacar worker de lista de activos cerrar driver
    dash.assigned_cards.remove(card)
    webdriver.quit()
