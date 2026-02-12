from datetime import datetime as dt
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="seleniumwire")

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_satmul
from src.utils.webdriver import ChromeUtils


def gather(placas, headless=True):
    chromedriver = ChromeUtils()
    webdriver = chromedriver.proxy_driver(residential=False, headless=headless)

    for placa in placas:
        try:
            scraper_response = scrape_satmul.browser_wrapper(placa, webdriver)
            if isinstance(scraper_response, str):
                print("Error SATMUL:", scraper_response)
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

            # if there is data in response, enter into database, go to next placa
            for resp in scraper_response:
                # adjust date to match db format (YYYY-MM-DD)
                _n = date_to_db_format(data=resp)
                print(
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

        except KeyboardInterrupt:
            quit()

        except Exception as e:
            print(f"SATMUL ({placa}): Crash: {str(e)}")
            break

    webdriver.quit()


if __name__ == "__main__":
    placas = ["CHO571", "AZK376"]
    gather(placas)
