from src.utils.constants import AUTOSCRAPER_REPETICIONES
from src.utils.utils import send_pushbullet
from src.comms import generar_mensajes
import time
from datetime import datetime as dt


def flujo(self, tipo_mensaje):

    # intentar una cantidad de veces actualizar el 100% de pendientes
    repetir = 0
    while True:

        # solicitar alertas/boletines pendientes para enviar a actualizar
        if tipo_mensaje == "alertas":
            self.datos_alerta()
        elif tipo_mensaje == "boletines":
            self.datos_boletin()

        # tomar datos pendientes de ser actualizados del atributo
        pendientes = self.actualizar_datos.json()

        # si ya no hay actualizaciones pendientes, siguiente paso
        if all([len(j) == 0 for j in pendientes.values()]):
            return True

        self.actualizar()

        # aumentar contador de repeticiones, si excede limite parar
        repetir += 1
        if repetir > AUTOSCRAPER_REPETICIONES:
            return False

        # reintentar scraping
        time.sleep(3)


def enviar_notificacion(mensaje):
    title = f"NoPasaNada AUTOSCRAPER - {dt.now()}"
    mensaje = "\n".join([i for i in mensaje])
    send_pushbullet(title=title, message=mensaje)


def main(self):

    if not self.config_autoscraper:
        self.log(action="[ AUTOSCRAPER ] OFFLINE")
        return

    # determinar cantidad de alertas y boletines que hay por procesar
    try:
        por_procesar = [
            sum(
                [
                    0 if not i.get(t) else int(i[t])
                    for i in self.data["scrapers_kpis"].values()
                ]
            )
            for t in ("alertas", "boletines")
        ]

        # procesar alertas si hay pendientes
        exito1 = True
        if por_procesar[0]:
            exito1 = flujo(self, tipo_mensaje="alertas")

        # procesar boletines si hay pendientes
        exito2 = True
        if por_procesar[1]:
            exito2 = flujo(self, tipo_mensaje="boletines")

        if exito1 and exito2:
            # generar y enviar mensajes
            generar_mensajes.alertas(db=self.db)
            generar_mensajes.boletines(db=self.db)

            self.server.enviar_correo_mensajes.send(db=self.db)
            if self.config_enviar_pushbullet:
                enviar_notificacion(mensaje="Nuevos mensajes enviados")

            # informar proceso completo y volver
            self.log(action="[ AUTOSCRAPER ] OK")
            return

        # informar proceso no puedo terminar
        self.log(action="[ AUTOSCRAPER ] NO TERMINO.")

    except Exception as e:
        print(f"Error {e}")
