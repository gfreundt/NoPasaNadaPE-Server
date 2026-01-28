from datetime import datetime as dt

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_brevete
from src.utils.webdriver import ChromeUtils


def gather(d):
    # construir webdriver con parametros especificos
    chromedriver = ChromeUtils()

    for id_member, _, doc_num in d:
        try:
            webdriver = chromedriver.proxy_driver(residential=True)
            scraper_response = scrape_brevete.browser_wrapper(
                doc_num=doc_num, webdriver=webdriver
            )

            # si respuesta es texto, hubo un error -- regresar
            if isinstance(scraper_response, str):
                print("Error Brevete:", scraper_response)
                continue

            # respuesta es en blanco
            if not scraper_response:
                print(
                    {
                        "Empty": True,
                        "IdMember_FK": id_member,
                    }
                )
                continue

            # ajustar formato de fechas al de la base de datos (YYYY-MM-DD)
            _n = date_to_db_format(data=scraper_response)

            # agregar registo a acumulador de respuestas (compartido con otros scrapers)

            respuesta = {
                "IdMember_FK": id_member,
                "Clase": _n[0],
                "Numero": _n[1],
                "Tipo": _n[2],
                "FechaExp": _n[3],
                "Restricciones": _n[4],
                "FechaHasta": _n[5],
                "Centro": _n[6],
                "Puntos": _n[7],
                "Record": _n[8],
                "LastUpdate": dt.now().strftime("%Y-%m-%d"),
            }
            print(respuesta)
            webdriver.quit()

        except KeyboardInterrupt:
            quit()

        except Exception as e:
            print(f"Brevete ({doc_num}): Crash: {str(e)}")
            break

    # sacar worker de lista de activos cerrar driver
    webdriver.quit()


if __name__ == "__main__":
    d = [(31, "09488838)"), (32, "71237579")]
    gather(d)
