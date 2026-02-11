import time
import random
import logging
from datetime import datetime as dt

from src.test.test_data import get_test_data
from src.test import (
    brevete_manual,
    calmul_manual,
    satimp_manual,
    satmul_manual,
    soat_manual,
    recvehic_manual,
    revtec_manual,
    sutran_manual,
)
from src.utils.utils import send_pushbullet
from src.comms import enviar_correo_interno

logger = logging.getLogger(__name__)


def main(self, size=1):

    logger.info(f"Iniciando prueba de scrapers con {size} registro(s) cada uno.")
    sample_size = [size] * 9
    data_pruebas = get_test_data(sample_size=sample_size)
    logger.debug(f"Datos de prueba obtenidos: {data_pruebas}")

    tests = [
        {
            "name": "Brevete Manual Test",
            "fn": brevete_manual.gather,
            "data": data_pruebas["DataMtcBrevetes"],
        },
        {
            "name": "Calmúl Manual Test",
            "fn": calmul_manual.gather,
            "data": data_pruebas["DataCallaoMultas"],
        },
        {
            "name": "SAT Impuesto Manual Test",
            "fn": satimp_manual.gather,
            "data": data_pruebas["DataSatImpuestos"],
        },
        {
            "name": "SAT Multas Manual Test",
            "fn": satmul_manual.gather,
            "data": data_pruebas["DataSatMultas"],
        },
        {
            "name": "SOAT Manual Test",
            "fn": soat_manual.gather,
            "data": data_pruebas["DataApesegSoats"],
        },
        {
            "name": "Record Vehicular Manual Test",
            "fn": recvehic_manual.gather,
            "data": data_pruebas["DataMtcRecordsConductores"],
        },
        {
            "name": "Revisión Técnica Manual Test",
            "fn": revtec_manual.gather,
            "data": data_pruebas["DataMtcRevisionesTecnicas"],
        },
        {
            "name": "SUTRAN Manual Test",
            "fn": sutran_manual.gather,
            "data": data_pruebas["DataSutranMultas"],
        },
    ]

    random.shuffle(tests)

    resultados, exitos, fallos = [], [], []

    for k, test in enumerate(tests, start=1):
        logger.info(f"\nScraper prueba {k}/{len(tests)} -- {test['name']}")
        start_time = time.perf_counter()

        try:
            test["fn"](test["data"])
            end_time = time.perf_counter()
            logger.info(
                f"✅ {test['name']}. Tiempo: {end_time - start_time:.2f} seconds"
            )
            resultados.append(1)
            exitos.append(test["name"])

        except Exception as e:
            logger.info(f"❌ {test['name']} failed: {e[:60]}...")
            resultados.append(0)
            fallos.append(test["name"])

    resultado = f"Prueba de scrapers completa (Total: {len(tests)}). Exitos: {sum(resultados)}. Fallos: {len(tests) - sum(resultados)}."
    logger.info(resultado)

    activity = send_pushbullet(
        title="Error en Prueba Scrapers",
        message=" - ".join([i for i in fallos]),
    )
    logger.info(f"Pushbullet Resultado Prueba Scrapers Enviado: {activity}")

    titulo = f"Resumen Diario ({str(dt.now())[:19]})"
    enviar_correo_interno.prueba_scrapers(titulo=titulo, mensaje=resultado)


if __name__ == "__main__":
    main()
