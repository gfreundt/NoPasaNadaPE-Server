from comms import enviar_mensajes
from src.utils.constants import AUTOSCRAPER_REPETICIONES
from src.utils.utils import send_pushbullet
from src.comms import generar_mensajes
from src.updates import datos_actualizar, do_actualizar
import time
from datetime import datetime as dt
from pprint import pformat
import logging

from updates import extrae_data_terceros

logger = logging.getLogger(__name__)


def main(self, tipo_mensaje):
    logger.info(f"[ AUTOMENSAJE {tipo_mensaje.upper()} ] Iniciando")

    # no activar si el switch de autoscraper esta apagado
    if not self.config_autoscraper:
        logger.warning(f"[ AUTOMENSAJE {tipo_mensaje.upper()} ] OFFLINE")
        self.log(action=f"[ AUTOMENSAJE {tipo_mensaje.upper()} ] OFFLINE")
        return

    # actualizar datos
    resultado = do_actualizar(self, tipo_mensaje)

    # datos actualizados correctamente: enviar mensajes
    if resultado:
        logger.info(f"Lanzando Enviar Mensajes: {tipo_mensaje.upper()}")
        do_enviar_mensajes(self, tipo_mensaje)
        return

    # datos no se puedieron actualizar: fin del proceso sin enviar mensajes
    return

    exito, fallo = flujo(self, tipo_mensaje=tipo_mensaje)

    if exito:
        logger.info(f"[ AUTOMENSAJE {tipo_mensaje.upper()} ] Proceso completo.")

        # generar mensajes
        a = generar_mensajes.alertas(db=self.db)
        if a > 0:
            self.log(action=f"[ AUTOSC {tipo_mensaje.upper()} ] Generado A: {a}")
            logger.info(f"[ AUTOSCRAPER {tipo_mensaje.upper()} ] Generado Alertas: {a}")
        b = generar_mensajes.boletines(db=self.db)
        if b > 0:
            self.log(action=f"[ AUTOSCRAPER {tipo_mensaje.upper()} ] Generado B: {b}")
            logger.info(
                f"[ AUTOSCREAPER {tipo_mensaje.upper()} ] Generado Boletines: {b}"
            )
        # enviar mensajes
        b, a = enviar_mensajes.send(db=self.db)
        if a > 0:
            self.log(action=f"[ AUTOSC {tipo_mensaje.upper()} ] Enviado A: {a}")
        if b > 0:
            self.log(action=f"[ AUTOSC {tipo_mensaje.upper()} ] Enviado B: {b}")
        if self.config_enviar_pushbullet:
            enviar_notificacion(
                mensaje=f"Nuevos mensajes enviados. ALERTAS: {a}. BOLETINES: {b}"
            )

        # informar proceso completo y volver
        self.log(action=f"[ AUTOSC {tipo_mensaje.upper()} ] OK")
        return

    else:
        logger.error(
            f"Autoscaper {tipo_mensaje}: Registros que no se actualizaron:\n {pformat(fallo)}"
        )

    # informar proceso no puedo terminar
    enviar_notificacion(mensaje="Error en Scraping!!")
    self.log(action=f"[ AUTOSC {tipo_mensaje.upper()} ] ERROR {fallo}")
