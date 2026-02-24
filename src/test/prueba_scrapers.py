import time
import logging
from datetime import datetime as dt

from src.test.test_data import get_test_data_new
from src.comms import enviar_correo_interno
from src.updates import gather_one_manual

logger = logging.getLogger(__name__)


def main(size=1):

    logger.info(f"Iniciando prueba de scrapers con {size} registro(s) cada uno.")

    # generar data de prueba
    pruebas = get_test_data_new(size)

    # iterar todas las pruebas
    positivo, negativo = [], []
    for k, data in enumerate(pruebas, start=1):
        logger.info(
            f"Lanzando scraper prueba {k}/{len(pruebas)} -- {data['Categoria']}"
        )
        start_time = time.perf_counter()
        try:
            respuesta = gather_one_manual.main(data, headless=True)
            if respuesta:
                end_time = time.perf_counter()
                logger.info(
                    f"Prueba Scraper {data['Categoria']}. Tiempo: {end_time - start_time:.2f} segundos"
                )
                positivo.append(data["Categoria"])
            else:
                logger.warning(f"Prueba Scraper {data['Categoria']} fallo simple")
                negativo.append(data["Categoria"])

        except KeyboardInterrupt:
            pass

        except Exception as e:
            logger.warning(
                f"Prueba Scraper {data['Categoria']} fallo total: {str(e)[:60]}..."
            )
            negativo.append(data["Categoria"])

    resultado = f"Prueba de scrapers completa (Total: {len(pruebas)}). Exitos: {len(positivo)}. Fallos: {len(negativo)}."
    resultado = (
        resultado + "\nScrapers con fallos: {', '.join(negativo)}"
        if negativo
        else resultado
    )
    logger.info(resultado)

    titulo = {
        "titulo": "Resultado Prueba de Scrapers",
        "subtitulo": str(dt.now())[:19],
    }
    print(resultado)
    enviar_correo_interno.prueba_scrapers(titulo=titulo, mensaje=resultado)


if __name__ == "__main__":
    main()
