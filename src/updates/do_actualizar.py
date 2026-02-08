import time
from pprint import pformat
from src.updates import datos_actualizar, gather_all_new
from src.utils.constants import AUTOSCRAPER_REPETICIONES
from src.utils.utils import send_pushbullet
import logging

logger = logging.getLogger(__name__)


def main(self, tipo_mensaje, max_repeticiones=AUTOSCRAPER_REPETICIONES):
    # intentar una cantidad de veces actualizar el 100% de pendientes
    repetir = 1

    while True:
        # solicitar alertas/boletines pendientes para enviar a actualizar
        if tipo_mensaje == "alertas":
            pendientes = datos_actualizar.get_datos_alertas(self)

        elif tipo_mensaje == "boletines":
            pendientes = datos_actualizar.get_boletines_para_actualizar(self)

        logger.info(
            f"[ AUTOMENSAJES {tipo_mensaje.upper()} ({repetir}/{AUTOSCRAPER_REPETICIONES}) ] Pendientes Actualizar:\n {pformat(pendientes)}"
        )

        # si ya no hay actualizaciones pendientes, regresar True
        if all([len(j) == 0 for j in pendientes.values()]):
            logger.info(
                "Actualizacion completa regular (o no habian datos por actualizar)."
            )
            return True

        # realizar scraping
        gather_all_new.main(self, pendientes)

        # aumentar contador de repeticiones, si excede limite parar
        repetir += 1
        if repetir > max_repeticiones:
            title = f"NoPasaNada AUTOSCRAPER"
            send_pushbullet(
                title=title, message="No se puedo completar actualizaciones."
            )
            return False

        time.sleep(3)
