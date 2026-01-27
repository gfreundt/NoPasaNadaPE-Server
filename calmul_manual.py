from datetime import datetime as dt

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_calmul
from src.utils.webdriver import ChromeUtils


def gather(placas):
    chromedriver = ChromeUtils()
    webdriver = chromedriver.proxy_driver(residential=False)

    for placa in placas:
        try:
            scraper_response = scrape_calmul.browser_wrapper(
                placa=placa, webdriver=webdriver
            )

            # si respuesta es texto, hubo un error -- regresar
            if isinstance(scraper_response, str):
                print("Error", scraper_response)
                continue

            if not scraper_response:
                print(
                    {
                        "Empty": True,
                        "PlacaValidate": placa,
                    }
                )
                continue

            for response in scraper_response:
                # ajustar formato de fechas al de la base de datos (YYYY-MM-DD)
                _n = date_to_db_format(data=response)

                # agregar registo a acumulador de respuestas (compartido con otros scrapers)
                print(
                    {
                        "PlacaValidate": placa,
                        "Codigo": _n[1],
                        "NumeroPapeleta": _n[2],
                        "FechaInfraccion": _n[3],
                        "TotalInfraccion": _n[4],
                        "TotalBeneficio": _n[5],
                        "ImageBytes": "",
                        "LastUpdate": dt.now().strftime("%Y-%m-%d"),
                    }
                )

        except KeyboardInterrupt:
            quit()

        except Exception as e:
            print("Exception", e)

    webdriver.quit()


if __name__ == "__main__":
    placas = ["CHO571", "AZK376"]
    gather(placas)
