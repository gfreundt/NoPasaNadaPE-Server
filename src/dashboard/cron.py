import schedule
import threading
import time
from src.dashboard import auto_scraper, update_kpis, resumen_diario
from src.utils import mantenimiento


def run_scheduler_loop(self):

    # activar al iniciar
    update_kpis.main(self)
    auto_scraper.main(self, "boletines")
    auto_scraper.main(self, "alertas")

    # varias veces al dia
    schedule.every(15).minutes.do(update_kpis.main, self)
    schedule.every(20).minutes.do(auto_scraper.main, self, "boletines")
    schedule.every(4).hours.do(auto_scraper.main, self, "alertas")
    schedule.every().hour.do(mantenimiento.cada_hora, self)

    # una vez al dia
    schedule.every().day.at('07:05').do(resumen_diario.main, self)

    while True:
        schedule.run_pending()
        time.sleep(1)


def main(self):
    t = threading.Thread(target=run_scheduler_loop, args=(self,), daemon=True)
    self.log(action="[ SERVICIO ] CRON: Activado")
    t.start()
