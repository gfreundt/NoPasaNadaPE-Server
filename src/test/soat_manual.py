from datetime import datetime as dt, timedelta as td
from func_timeout import exceptions
from requests.exceptions import RequestException, ReadTimeout


# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_soat as scraper
from src.utils.webdriver import ChromeUtils


def gather(data, headless=True):
    chromedriver = ChromeUtils()
    webdriver = chromedriver.proxy_driver(residential=False, headless=headless)

    for placa in data:
        scraper_response = scraper.browser_wrapper(placa=placa, webdriver=webdriver)

        try:
            # si respuesta es texto, hubo un error -- regresar
            if isinstance(scraper_response, str):
                print("Error SOAT:", scraper_response)

            # respuesta es en blanco
            if not scraper_response:
                print(
                    {
                        "Empty": True,
                        "PlacaValidate": placa,
                    }
                )
                continue

            # placa si tiene resultados
            _n = date_to_db_format(data=scraper_response)
            respuesta = {
                "IdPlaca_FK": 999,
                "Aseguradora": _n[0],
                "FechaInicio": _n[2],
                "FechaHasta": _n[3],
                "PlacaValidate": _n[4],
                "Certificado": _n[5],
                "Uso": _n[6],
                "Clase": _n[7],
                "Vigencia": _n[1],
                "Tipo": _n[8],
                "FechaVenta": _n[9],
                "ImageBytes": "Aca va la imagen",
                "LastUpdate": dt.now().strftime("%Y-%m-%d"),
            }
            print(respuesta)

        except KeyboardInterrupt:
            quit()

        except Exception as e:
            print(f"SOATS ({placa}): Crash: {str(e)}")
            break

    # sacar worker de lista de activos cerrar driver
    webdriver.quit()


if __name__ == "__main__":
    placas = ["CHO571", "AZK376"]
    gather(placas)
