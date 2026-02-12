from datetime import datetime as dt

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_sutran
from src.utils.webdriver import ChromeUtils


def gather(placas, headless=True):
    chromedriver = ChromeUtils()
    webdriver = chromedriver.proxy_driver(residential=False, headless=headless)

    for placa in placas:
        try:
            scraper_response = scrape_sutran.browser_wrapper(placa, webdriver)
            # si respuesta es texto, hubo un error -- regresar
            if isinstance(scraper_response, str):
                print("Error SUTRAN:", scraper_response)
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

            # iterate on all multas
            for resp in scraper_response:
                _n = date_to_db_format(data=resp)
                print(
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

        except KeyboardInterrupt:
            quit()

        except Exception as e:
            print(f"SUTRAN ({placa}): Crash: {str(e)}")
            break

    webdriver.quit()


if __name__ == "__main__":
    placas = ["CHO571", "AZK376"]
    gather(placas)
