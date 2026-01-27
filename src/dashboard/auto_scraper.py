from src.utils.constants import AUTOSCRAPER_REPETICIONES
from src.utils.utils import send_pushbullet
from src.comms import generar_mensajes, enviar_correo_mensajes
from src.updates import datos_actualizar, gather_all
import time
from datetime import datetime as dt
from pprint import pformat
import logging

logger = logging.getLogger(__name__)


def flujo(self, tipo_mensaje):
    # intentar una cantidad de veces actualizar el 100% de pendientes
    repetir = 0
    while True:
        # solicitar alertas/boletines pendientes para enviar a actualizar
        if tipo_mensaje == "alertas":
            pendientes = datos_actualizar.alertas(self)

        elif tipo_mensaje == "boletines":
            pendientes = datos_actualizar.boletines(self)

        logger.info(
            f"[ AUTOSCRAPER {tipo_mensaje.upper()} ] Pendientes:\n {pformat(pendientes)}"
        )

        # si ya no hay actualizaciones pendientes, regresar True
        if all([len(j) == 0 for j in pendientes.values()]):
            return True, None

        # realizar scraping
        tamano_actualizacion = gather_all.gather_threads(
            dash=self, all_updates=pendientes
        )

        # reportar en dashboard
        self.log(
            action=f"[ ACT {tipo_mensaje.upper()}] Data: {tamano_actualizacion} kB",
        )

        # aumentar contador de repeticiones, si excede limite parar
        repetir += 1
        if repetir > AUTOSCRAPER_REPETICIONES:
            return False, pendientes

        # reintentar scraping
        time.sleep(3)


def enviar_notificacion(mensaje):
    title = f"NoPasaNada AUTOSCRAPER - {dt.now()}"
    mensaje = "\n".join([i for i in mensaje])
    send_pushbullet(title=title, message=mensaje)


def main(self, tipo_mensaje):
    logger.info(f"[ AUTOSCRAPER {tipo_mensaje.upper()} ] Iniciando")

    # no activar si el switch de autoscraper esta apagado
    if not self.config_autoscraper:
        logger.info(f"Autoscaper Offline: {tipo_mensaje}")
        self.log(action=f"[ AUTOSC {tipo_mensaje.upper()} ] OFFLINE")
        return

    # procesar alertas/boletines
    exito, fallo = flujo(self, tipo_mensaje=tipo_mensaje)

    if exito:
        logger.info(f"[ AUTOSCRAPER {tipo_mensaje.upper()} ] Proceso completo.")

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
        b, a = enviar_correo_mensajes.send(db=self.db)
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
