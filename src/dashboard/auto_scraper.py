from src.utils.constants import AUTOSCRAPER_REPETICIONES
from src.utils.utils import send_pushbullet
from src.comms import generar_mensajes, enviar_correo_mensajes
from src.updates import datos_actualizar, gather_all
import time
from datetime import datetime as dt


def flujo(self, tipo_mensaje):

    # intentar una cantidad de veces actualizar el 100% de pendientes
    repetir = 0
    while True:

        # solicitar alertas/boletines pendientes para enviar a actualizar
        if tipo_mensaje == "alertas":
            pendientes = datos_actualizar.alertas(self)

        elif tipo_mensaje == "boletines":
            pendientes = datos_actualizar.boletines(self)

        # si ya no hay actualizaciones pendientes, regresar True
        print("*************", pendientes)
        if all([len(j) == 0 for j in pendientes.values()]):
            return True, None

        # realizar scraping
        tamano_actualizacion = gather_all.gather_threads(
            dash=self, all_updates=pendientes
        )

        # reportar en dashboard
        self.log(
            action=f"[ ACTUALIZACION {tipo_mensaje.upper()}] Tamaño: {tamano_actualizacion} kB",
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

    # no activar si el switch de autoscraper esta apagado
    if not self.config_autoscraper:
        self.log(action=f"[ AUTOSCRAPER {tipo_mensaje.upper()} ] OFFLINE")
        return

    # procesar alertas/boletines
    exito, falto = flujo(self, tipo_mensaje=tipo_mensaje)

    if exito:
        # generar y enviar mensajes
        generar_mensajes.alertas(db=self.db)
        generar_mensajes.boletines(db=self.db)

        enviar_correo_mensajes.send(db=self.db)
        if self.config_enviar_pushbullet:
            enviar_notificacion(mensaje="Nuevos mensajes enviados")

        # informar proceso completo y volver
        self.log(action=f"[ AUTOSCRAPER {tipo_mensaje.upper()} ] OK")
        return

    # informar proceso no puedo terminar
    enviar_notificacion(mensaje="Error en Scraping!!")
    self.log(action=f"[ AUTOSCRAPER {tipo_mensaje.upper()} ] NO TERMINO por {falto}")
