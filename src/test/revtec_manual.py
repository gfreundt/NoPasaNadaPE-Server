from datetime import datetime as dt
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="seleniumwire")

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_revtec
from src.utils.webdriver import ChromeUtils


def gather(placas, headless=True):
    chromedriver = ChromeUtils()
    webdriver = chromedriver.proxy_driver(residential=True, headless=headless)

    for placa in placas:
        try:
            scraper_response = scrape_revtec.browser_wrapper(
                placa=placa, webdriver=webdriver
            )

            if isinstance(scraper_response, str):
                print("Error Revisión Técnica:", scraper_response)
                continue

            # respuesta es en blanco
            if not scraper_response:
                print(
                    {
                        "Empty": True,
                        "PlacaValidate": placa,
                    }
                )
                continue

            # ajustar formato de fechas al de la base de datos (YYYY-MM-DD)
            _n = date_to_db_format(data=scraper_response)

            # agregar registo a acumulador de respuestas (compartido con otros scrapers)
            respuesta = {
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
            print(respuesta)

        except KeyboardInterrupt:
            quit()

        except Exception as e:
            print(f"Revisión Técnica ({placa}): Crash: {str(e)}")
            print("-----------")
            continue

    # sacar worker de lista de activos cerrar driver
    webdriver.quit()


if __name__ == "__main__":
    placas = ["CHO571", "AZK376"]
    gather(placas)
