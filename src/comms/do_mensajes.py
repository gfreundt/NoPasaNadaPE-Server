from src.utils.constants import AUTOSCRAPER_REPETICIONES
from src.utils.utils import send_pushbullet
from src.comms import generar_mensajes, enviar_correo_mensajes
from src.updates import datos_actualizar, gather_all_new, do_actualizar
import time
from datetime import datetime as dt
from pprint import pformat
import logging

logger = logging.getLogger(__name__)


def main(self, tipo_mensaje):
    logger.info(f"[ DO MENSAJES {tipo_mensaje.upper()} ] Iniciando")

    # no activar si el switch de autoscraper esta apagado
    if not self.config_autoscraper:
        logger.warning(f"[ DO MENSAJES {tipo_mensaje.upper()} ] OFFLINE")
        self.log(action=f"[ DO MENSAJES {tipo_mensaje.upper()} ] OFFLINE")
        return False

    # actualizar datos
    logger.info(f"Lanzando Actualizar Datos: {tipo_mensaje.upper()}")
    resultado = do_actualizar(self, tipo_mensaje)

    # datos actualizados correctamente: generar mensajes
    if resultado:
        logger.info(f"Lanzando Generar Mensajes: {tipo_mensaje.upper()}")
        resultado = generar_mensajes(self, tipo_mensaje)

        # hay mensajes generados - enviar mensajes
        if resultado:
            logger.info(f"Lanzando Enviar Mensajes: {tipo_mensaje.upper()}")
            resultado = enviar_mensajes(self, tipo_mensaje)

            # mensajes enviados correctamente - fin del proceso
            if resultado:
                return True

    # proceso no llego al final (error actualizando, no hay nuevos mensajes generados o no se pudieron enviar)
    return False
