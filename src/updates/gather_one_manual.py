import logging
from pprint import pformat
from func_timeout import func_timeout

from src.scrapers import configuracion_scrapers
from src.utils.utils import date_to_db_format
from src.utils.webdriver import ChromeUtils


logger = logging.getLogger(__name__)


def main(dato, headless=True):
    """
    Ejecuta la extraccion de data de servicios de terceros y simula el armado del payload de respuesta
    No esta en try-except porque el control del fallo lo lleva el script de prueba de scrapers (prueba_scrapers.py)
    """

    # obtiene datos completos de configuraciones de scrapers
    config = configuracion_scrapers.config(dato["Categoria"])

    # lanzar scraper via webdriver o API dependiendo de configuracion del scraper, con timeout definido en configuracion
    func_scraper = config["funcion_scraper"]
    logger.info(f"Prueba Scraper {dato['Categoria']}: Indice: {dato}.")

    # api
    if config["api"]:
        respuesta_scraper = func_scraper.api(
            datos=dato,
            timeout=config["timeout"],
        )

    # webdriver
    else:
        chromedriver = ChromeUtils()

        # crear webdriver con proxy residencial dependiendo de configuracion del scraper
        webdriver = chromedriver.proxy_driver(
            residential=config["residential_proxy"],
            headless=headless,
        )

        # ejectuar scraper con timeout definido en configuracion
        try:
            respuesta_scraper = func_timeout(
                config["timeout"],
                func_scraper.browser,
                kwargs={
                    "datos": dato,
                    "webdriver": webdriver,
                },
            )

        finally:
            webdriver.quit()

    logger.debug(
        f"Respuesta Prueba Scraper {dato['Categoria']}: {pformat(respuesta_scraper)}"
    )

    # si respuesta de scraper es texto, hubo un error y se regresa False
    if isinstance(respuesta_scraper, str):
        return False

    # en caso respuesta tenga data - probar armar payload con estructura de configuracion del scraper
    payload = []
    for item in respuesta_scraper:
        item_formateado = date_to_db_format(item)
        parte_payload = {
            key: item_formateado[pos] if pos is not None else ""
            for key, pos in config["estructura_respuesta"].items()
        }
        parte_payload.update({"Categoria": dato["Categoria"]})
        payload.append(parte_payload)

    # regresa True si no han habido errores
    return True
