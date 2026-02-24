import time
from pprint import pformat
from src.updates import datos_actualizar, extrae_data_terceros
from src.utils.constants import AUTOSCRAPER_REPETICIONES
from src.utils.utils import send_pushbullet
from src.server import do_updates
import logging

logger = logging.getLogger(__name__)


def main(db, tipo_mensaje, max_repeticiones=AUTOSCRAPER_REPETICIONES):
    """
    Intenta una cantidad de veces de actualizar todo lo pendiente de Boletines o Alertas.
    Luego graba lo que logra actualizar en la base de datos.
    Si logra actualizar todo retorna True.
    Si algo no logra actualizar o no hubo nada por actualizar retorna False.
    """

    cuenta_repeticiones = 1

    while True:
        # solicitar alertas/boletines pendientes para enviar a actualizar (pre-mensaje)
        if tipo_mensaje == "alertas":
            pendientes = datos_actualizar.get_datos_alertas(db, premensaje=True)

        elif tipo_mensaje == "boletines":
            pendientes = datos_actualizar.get_datos_boletines(db, premensaje=True)

        titulo = f"[ DO ACTUALIZAR {tipo_mensaje.upper()} ({cuenta_repeticiones}/{AUTOSCRAPER_REPETICIONES}) ]"

        logger.info(f"{titulo} Pendientes Actualizar:\n {pformat(pendientes)}")

        # si ya no hay actualizaciones pendientes, regresar True si hubieron actualizaciones, False si no hubieron
        if not pendientes:
            if cuenta_repeticiones == 1:
                logger.info(
                    f"{titulo} Fin Normal. No hubieron actualizaciones. Fin del Proceso."
                )
                return False
            else:
                logger.info(f"{titulo} Fin Normal. Si hubieron actualizaciones.")
                return True

        # realizar scraping
        respuesta = extrae_data_terceros.main(db, pendientes)

        # actualizar base de datos con lo que haya sido devuelto (completo o parcial)
        logger.info(
            f"[ AUTOMENSAJES {tipo_mensaje.upper()} Enviando a actualizar base de datos {pformat(respuesta)}"
        )
        do_updates.main(db, data=respuesta)

        # aumentar contador de repeticiones, si excede limite parar
        cuenta_repeticiones += 1
        if cuenta_repeticiones > max_repeticiones:
            title = "NoPasaNada AUTOMENSAJES"
            send_pushbullet(
                title=title, message="No se puedo completar actualizaciones."
            )
            return False

        time.sleep(3)
