import time
import threading

from src.dashboard import auto_scraper, update_kpis
from src.updates import datos_actualizar


def thread(self):

    while True:

        # 1. Actualiza los KPIs de servicios de terceros (truecaptcha, etc..)
        update_kpis.main(self)

        # 2. Actualiza alertas y boletines por procesar
        datos_actualizar.alertas(self.db)
        datos_actualizar.boletines(self.db)

        # 3. Empieza el scraping automatico
        auto_scraper.main(self)

        # 99. Espera dos minutos antes de volver a empezar
        time.sleep(15)


def main(self):
    t = threading.Thread(target=thread, args=(self,), daemon=True)
    self.log(action="[ SERVICIO ] CRON: Activado")
    t.start()
