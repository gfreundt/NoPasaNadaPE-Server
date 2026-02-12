from datetime import datetime as dt

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_brevete
from src.utils.webdriver import ChromeUtils


def gather(dato_prueba, headless=True):
    # construir webdriver con parametros especificos
    chromedriver = ChromeUtils()

    id_member, _, doc_num = dato_prueba
    try:
        webdriver = chromedriver.proxy_driver(residential=True, headless=headless)
        scraper_response = scrape_brevete.browser_wrapper(
            doc_num=doc_num, webdriver=webdriver
        )

        # si respuesta es texto, hubo un error -- regresar
        if isinstance(scraper_response, str):
            return False, scraper_response

        # respuesta es en blanco
        if not scraper_response:
            return True, None

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
        return True, None

    except Exception as e:
        return False, e


if __name__ == "__main__":
    d = [(31, "DNI", "09488838"), (32, "DNI", "71237579")]
    gather(d)
