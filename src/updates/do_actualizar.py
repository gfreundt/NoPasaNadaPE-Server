import time
from pprint import pformat
from src.updates import datos_actualizar, gather_all_new
from src.utils.constants import AUTOSCRAPER_REPETICIONES
from src.utils.utils import send_pushbullet
from src.server import do_updates
import logging

logger = logging.getLogger(__name__)


def main(self, tipo_mensaje, max_repeticiones=AUTOSCRAPER_REPETICIONES):
    # intentar una cantidad de veces actualizar el 100% de pendientes
    repetir = 1

    while True:
        # solicitar alertas/boletines pendientes para enviar a actualizar (pre-mensaje)
        if tipo_mensaje == "alertas":
            pendientes = datos_actualizar.get_datos_alertas(self, premensaje=True)

        elif tipo_mensaje == "boletines":
            pendientes = datos_actualizar.get_datos_boletines(self, premensaje=True)

        titulo = f"[ DO ACTUALIZAR {tipo_mensaje.upper()} ({repetir}/{AUTOSCRAPER_REPETICIONES}) ]"

        logger.info(f"{titulo} Pendientes Actualizar:\n {pformat(pendientes)}")

        # si ya no hay actualizaciones pendientes, regresar True
        if not pendientes:
            logger.info(f"{titulo} Fin Normal.")
            return True

        # realizar scraping
        respuesta = gather_all_new.main(self, pendientes)

        # actualizar base de datos con lo que haya sido devuelto (completo o parcial)
        logger.info(
            f"[ AUTOMENSAJES {tipo_mensaje.upper()} Enviando a actualizar base de datos {pformat(respuesta)}"
        )
        do_updates.main(self, data=respuesta)

        # aumentar contador de repeticiones, si excede limite parar
        repetir += 1
        if repetir > max_repeticiones:
            title = "NoPasaNada AUTOSCRAPER"
            send_pushbullet(
                title=title, message="No se puedo completar actualizaciones."
            )
            return False

        time.sleep(3)
