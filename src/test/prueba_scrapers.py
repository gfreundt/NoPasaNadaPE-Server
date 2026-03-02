import time
import logging
from datetime import datetime as dt

from src.test.test_data import get_test_data_new
from src.comms import enviar_correo_interno
from src.updates import gather_one_manual

logger = logging.getLogger(__name__)


def main():
    """
    Prueba todos los scrapers de forma secuencial.
    Usa data elegida al azar de una lista de data de prueba.
    """

    titulo_log = "[PRUEBA SCRAPERS]"

    logger.info(f"{titulo_log} Iniciando proceso con 1 registro cada uno.")

    # generar data de prueba
    pruebas = get_test_data_new(s=1)

    # iterar todas las pruebas
    positivo, negativo_simple, negativo_total = [], [], []
    for k, data in enumerate(pruebas, start=1):
        logger.info(f"{titulo_log} Probando {k}/{len(pruebas)} -- {data['Categoria']}")
        start_time = time.perf_counter()

        try:
            respuesta = gather_one_manual.main(data, headless=True)

            if respuesta:
                end_time = time.perf_counter()
                logger.info(
                    f"{titulo_log} {data['Categoria']} ok. Tiempo: {end_time - start_time:.2f} segundos"
                )
                positivo.append(data["Categoria"])

            else:
                logger.warning(f"{titulo_log} {data['Categoria']} fallo simple")
                negativo_simple.append(data["Categoria"])

        except Exception:
            logger.exception(f"{titulo_log} {data['Categoria']} fallo total.")
            negativo_total.append(data["Categoria"])

    # armar texto con resultado y enviar por correo
    resultado = f"{titulo_log} Completa (Total: {len(pruebas)}). Exitos: {len(positivo)}. Fallos Simples: {len(negativo_simple)}. Fallos Totales: {len(negativo_total)}"
    resultado += f"\n Scrapers Ok: {','.join(positivo) or 'Ninguno'}."
    resultado += f"\n Scrapers Fallo Simple: {','.join(negativo_simple) or 'Ninguno'}."
    resultado += f"\n Scrapers Fallo Total: {','.join(negativo_total) or 'Ninguno'}."
    titulo_correo = {
        "titulo": "Resultado Prueba de Scrapers",
        "subtitulo": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    enviar_correo_interno.prueba_scrapers(titulo=titulo_correo, mensaje=resultado)

    logger.info(f"{titulo_log} Correo Enviado. Proceso completo. {resultado}")


if __name__ == "__main__":
    main()
