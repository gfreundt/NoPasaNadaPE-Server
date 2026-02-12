from func_timeout import func_timeout
from func_timeout.exceptions import FunctionTimedOut
from src.scrapers import configuracion_scrapers
from src.utils.utils import date_to_db_format
from src.utils.webdriver import ChromeUtils
import time
from pprint import pformat
import logging

logger = logging.getLogger(__name__)


def main(self, dato, headless=True):

    print(dato)

    config = configuracion_scrapers.config(dato["Categoria"])
    chromedriver = ChromeUtils()
    webdriver = chromedriver.proxy_driver(
        residential=config["residential_proxy"], headless=headless
    )

    # definir datos necesarios para el scraper
    if config["indice_placa"]:
        datos_scraper = dato["Placa"]
    else:
        datos_scraper = (dato["DocTipo"], dato["DocNum"])

    # lanzar scraper dentro de un wrapper para timeout
    try:
        func_scraper = config["funcion_scraper"]
        logger.info(f"Prueba Scraper {dato['Categoria']}: Indice: {datos_scraper}.")
        respuesta_scraper = func_timeout(
            config["timeout"], func_scraper.browser, args=(datos_scraper, webdriver)
        )
        logger.debug(
            f"Respuesta Prueba Scraper {dato['Categoria']}: {pformat(respuesta_scraper)}"
        )

        # si respuesta es texto, hubo un error -- reponer dato a cola y vuelve sin actualizar acumulador
        if isinstance(respuesta_scraper, str):
            return False

        # en caso respuesta tenga data - armar payload como lista de respuestas de scraper
        payload = []
        for item in respuesta_scraper:
            item_formateado = date_to_db_format(item)
            parte_payload = {
                key: item_formateado[pos] if pos is not None else ""
                for key, pos in config["estructura_respuesta"].items()
            }
            payload.append(parte_payload)

        # cierra webdriver y regresa True si no han habido errores
        time.sleep(1)
        webdriver.quit()
        return True

    # scraper no termino a tiempo, se devuelve dato a la cola y regresa al recolector
    except FunctionTimedOut:
        return False
