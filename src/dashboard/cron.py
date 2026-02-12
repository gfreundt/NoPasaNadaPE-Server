import schedule
import threading
import time
import logging
from pprint import pformat

from src.dashboard import resumen_diario
from src.comms import do_mensajes
from src.utils import mantenimiento
from src.test import prueba_scrapers


logger = logging.getLogger(__name__)


def run_scheduler_loop(self):

    # TEST: generar boletin fijo
    # from src.test import crear_boletin
    # crear_boletin.main(self, idmember="25", correo="gabfre@gmail.com")
    # return

    # TEST: prueba scrapers
    # prueba_scrapers.main(self, 1)
    # return

    # TEST: ocr de sunarp
    from src.test import ocrspace

    ocrspace.main(self)

    return

    # 1. Boletines a las hh:05 entre 7am y 8pm (inclusive)
    for hour in range(7, 21):
        schedule.every().day.at(f"{hour:02d}:05").do(
            do_mensajes.main, self, "boletines"
        ).tag("boletines")

    # 2. Alertas dos veces al dia (8:30am y 3:30pm)
    schedule.every().day.at("08:30").do(do_mensajes.main, self, "alertas").tag(
        "alertas"
    )
    schedule.every().day.at("15:30").do(do_mensajes.main, self, "alertas").tag(
        "alertas"
    )

    # 3. Resumen diario (del dia anterior), diariamente a la 1am
    schedule.every().day.at("01:00").do(resumen_diario.main, self).tag("resumen_diario")

    # 4. Prueba de scrapers diariamente a las 6:30am
    schedule.every().day.at("06:30").do(prueba_scrapers.main, self).tag(
        "prueba_scrapers"
    )

    # 5. Mantenimiento a las hh:45 permanentenemente
    for hour in range(0, 24):
        schedule.every().day.at(f"{hour:02d}:45").do(mantenimiento.cada_hora, self).tag(
            "mantenimiento"
        )

    logger.debug(
        f"Cron scheduler iniciado. Tareas programadas: \n{pformat(schedule.get_jobs())}"
    )

    logger.info(
        f"Cron scheduler iniciado. Tareas programadas: {len(schedule.get_jobs())}"
    )

    for job in sorted(schedule.get_jobs(), key=lambda j: j.next_run)[:10]:
        logger.info(f"Siguiente Tarea: {job.next_run} -> {job.tags}")

    # ejecutar al iniciar
    # do_mensajes.main(self, "boletines")
    # do_mensajes.main(self, "alertas")

    while True:
        schedule.run_pending()
        time.sleep(10)


def main(self):
    time.sleep(3)
    t = threading.Thread(target=run_scheduler_loop, args=(self,), daemon=True)
    self.log(action="[ SERVICIO ] CRON: Activado")
    t.start()
