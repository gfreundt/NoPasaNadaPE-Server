import schedule
import threading
import time
import logging

from src.dashboard import update_kpis, resumen_diario
from src.comms import do_mensajes
from src.utils import mantenimiento
from src.test import prueba_scrapers


logger = logging.getLogger(__name__)


def run_scheduler_loop(self):

    # TEST: generar boletin fijo
    # from src.test import crear_boletin
    # crear_boletin.main(self, idmember="25", correo="gabfre@gmail.com")
    # return

    # programar varias veces al dia
    schedule.every(15).minutes.do(update_kpis.main, self)
    schedule.every(60).minutes.do(do_mensajes.main, self, "boletines")
    schedule.every().hour.do(mantenimiento.cada_hora, self)

    # programar una vez al dia
    schedule.every().day.at("07:05").do(resumen_diario.main, self)
    # schedule.every().day.at("07:10").do(prueba_scrapers.main, self)
    schedule.every().day.at("07:30").do(do_mensajes.main, self, "alertas")
    schedule.every().day.at("15:00").do(do_mensajes.main, self, "alertas")

    logger.info(
        f"Cron scheduler iniciado. Tareas programadas: {len(schedule.get_jobs())}."
    )

    # ejecutar al iniciar
    # update_kpis.main(self)
    do_mensajes.main(self, "boletines")
    do_mensajes.main(self, "alertas")

    while True:
        schedule.run_pending()
        time.sleep(10)


def main(self):
    t = threading.Thread(target=run_scheduler_loop, args=(self,), daemon=True)
    self.log(action="[ SERVICIO ] CRON: Activado")
    t.start()
