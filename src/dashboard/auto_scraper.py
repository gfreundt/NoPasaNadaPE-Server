from src.utils.constants import AUTOSCRAPER_REPETICIONES
from src.utils.utils import send_pushbullet, start_vpn, stop_vpn
import time
from datetime import datetime as dt


def flujo(self, tipo_mensaje):

    # intentar una cantidad de veces actualizar el 100% de pendientes
    repetir = 0
    _first = True
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
            stop_vpn()
            self.vpn_location == ""
            return True

        else:

            if _first:
                iniciar_vpn_ideal(self, pendientes)
                self.actualizar()
                _first = False
                continue

            else:

                # reevaluar si se debe cambiar de pais de VPN
                iniciar_vpn_ideal(self, pendientes)
                self.actualizar()

                # aumentar contador de repeticiones, si excede limite parar
                repetir += 1
                if repetir > AUTOSCRAPER_REPETICIONES:
                    return False

                # reintentar scraping
                time.sleep(3)


def iniciar_vpn_ideal(self, pendientes):

    if not self.config_obligar_vpn:
        return

    # determinar si se necesita solo brevete y recvehic o algo mas
    solo_mtc = True
    for key, value_list in pendientes.items():
        if key not in {"brevetes", "recvehic"}:
            if value_list:
                solo_mtc = False
                break

    # si solo se necesitan servicios mtc, pais debe ser AR
    pais_necesario = "AR" if solo_mtc else "PE"

    # VPN ya esta en pais necesario, no cambiar VPN
    if self.vpn_location == pais_necesario:
        self.log(action=f"[ VPN MANTIENE ( {self.vpn_location} )]")
        return
    else:
        self.vpn_location = pais_necesario

    # para actual pais y empezar el nuevo
    stop_vpn()
    start_vpn(self.vpn_location)
    self.log(action=f"[ VPN PRENDIDA ( {self.vpn_location} )]")


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
            self.generar_alertas()
            self.generar_boletines()

            self.enviar_mensajes()
            if self.config_enviar_pushbullet:
                enviar_notificacion(mensaje="Nuevos mensajes enviados")

            # informar proceso completo y volver
            self.log(action="[ AUTOSCRAPER ] OK")
            return

        # informar proceso no puedo terminar
        self.log(action="[ AUTOSCRAPER ] NO TERMINO.")

    except Exception as e:
        print(f"Error {e}")
