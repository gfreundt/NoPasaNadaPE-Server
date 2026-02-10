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

    from src.comms import generar_mensajes
    from jinja2 import Environment, FileSystemLoader
    import os
    from src.utils.constants import NETWORK_PATH
    import uuid

    # Load HTML template
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("comms-maquinarias-boletin.html")
    cursor = self.db.cursor()
    IdMember = "25"
    subject = ("Alerta de NoPasaNada PE",)
    correo = "gabfre@gmail.com"
    mensaje = generar_mensajes.redactar_boletin(
        cursor, IdMember, template, subject, correo
    )
    # solo para ver html
    path = os.path.join(
        NETWORK_PATH,
        "outbound",
        "temp",
        f"boletin_{uuid.uuid4().hex[:8]}.html",
    )
    with open(path, "w", encoding="utf-8") as file:
        file.write(mensaje["html"])
    return

    # programar varias veces al dia
    schedule.every(15).minutes.do(update_kpis.main, self)
    schedule.every(30).minutes.do(do_mensajes.main, self, "boletines")
    schedule.every().hour.do(mantenimiento.cada_hora, self)

    # programar una vez al dia
    schedule.every().day.at("07:05").do(resumen_diario.main, self)
    schedule.every().day.at("07:10").do(prueba_scrapers.main, self)
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
