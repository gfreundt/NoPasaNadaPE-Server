import schedule
import threading
import time
import logging

from src.dashboard import auto_scraper, update_kpis, resumen_diario
from src.utils import mantenimiento
from src.test import prueba_scrapers


logger = logging.getLogger(__name__)


def run_scheduler_loop(self):
    from src.updates import datos_actualizar
    from src.updates import gather_all_new

    time.sleep(3)
    c = datos_actualizar.get_alertas_para_mensajes(self)
    print(c)
    gather_all_new.main(self, c)

    # programar varias veces al dia
    schedule.every(15).minutes.do(update_kpis.main, self)
    schedule.every(20).minutes.do(auto_scraper.main, self, "boletines")
    schedule.every().hour.do(
        mantenimiento.cada_hora, self
    )  # reemplazar por trigger luego de cargar sunarp

    # programar una vez al dia
    schedule.every().day.at("07:05").do(resumen_diario.main, self)
    schedule.every().day.at("07:10").do(prueba_scrapers.main, self)
    schedule.every().day.at("07:30").do(auto_scraper.main, self, "alertas")
    schedule.every().day.at("15:00").do(auto_scraper.main, self, "alertas")

    logger.info(
        f"Cron scheduler iniciado. Tareas programadas: {len(schedule.get_jobs())}."
    )

    # ejecutar al iniciar
    update_kpis.main(self)
    auto_scraper.main(self, "boletines")
    auto_scraper.main(self, "alertas")

    while True:
        schedule.run_pending()
        time.sleep(10)


def main(self):
    t = threading.Thread(target=run_scheduler_loop, args=(self,), daemon=True)
    self.log(action="[ SERVICIO ] CRON: Activado")
    t.start()
