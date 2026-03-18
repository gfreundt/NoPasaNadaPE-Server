import time
import logging
from datetime import datetime as dt

from src.server import genera_data_pruebas
from src.comms import enviar_correo_interno
from src.updates import gather_one_manual

logger = logging.getLogger(__name__)


def main():
    """
    Prueba todos los scrapers de forma secuencial.
    Usa data elegida al azar de una lista de data de prueba.
    Arma y envia datos para correo informativo.
    """

    titulo_log = "[PRUEBA SCRAPERS]"

    logger.info(f"{titulo_log} Iniciando proceso con 1 registro cada uno.")

    # generar data de prueba
    pruebas = genera_data_pruebas.generar(tamano_muestra=1)

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

    # armar texto con titulo, resumen y resultados y enviar por correo
    titulos = {
        "titulo": "Resultado Prueba de Scrapers",
        "subtitulo": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    resumen = {
        "total": len(pruebas),
        "exitos": len(positivo),
        "fallos_simples": len(negativo_simple),
        "fallos_totales": len(negativo_total),
    }
    resultados = {
        "ok": positivo,
        "fallos_simples": negativo_simple,
        "fallos_totales": negativo_total,
    }

    enviar_correo_interno.prueba_scrapers(
        mensaje={"titulos": titulos, "resumen": resumen, "resultados": resultados}
    )

    logger.info(f"{titulo_log} Correo Enviado. Proceso completo. {resultados}")
