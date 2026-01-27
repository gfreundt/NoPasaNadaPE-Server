import schedule
import threading
import time
import logging

from src.dashboard import auto_scraper, update_kpis, resumen_diario
from src.utils import mantenimiento


logger = logging.getLogger(__name__)


def run_scheduler_loop(self):
    # ejecutar varias veces al dia
    schedule.every(15).minutes.do(update_kpis.main, self)
    schedule.every(20).minutes.do(auto_scraper.main, self, "boletines")
    schedule.every(4).hours.do(auto_scraper.main, self, "alertas")
    schedule.every().hour.do(mantenimiento.cada_hora, self)

    # ejecutar una vez al dia
    schedule.every().day.at("07:05").do(resumen_diario.main, self)

    logger.info(
        f"Cron scheduler iniciado. Tareas programadas: {len(schedule.get_jobs())}."
    )

    # ejecutar al iniciar
    update_kpis.main(self)
    auto_scraper.main(self, "boletines")
    auto_scraper.main(self, "alertas")

    while True:
        schedule.run_pending()
        time.sleep(1)


def main(self):
    t = threading.Thread(target=run_scheduler_loop, args=(self,), daemon=True)
    self.log(action="[ SERVICIO ] CRON: Activado")
    t.start()
