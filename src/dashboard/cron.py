import time
import threading

from src.dashboard import auto_scraper, update_kpis


def thread(self):

    while True:

        # 1. Actualiza los KPIs de servicios de terceros (truecaptcha, etc..)
        update_kpis.main(self)

        # 2. Actualiza alertas y boletines por procesar
        self.datos_alerta()
        self.datos_boletin()

        # 3. Empieza el scraping automatico
        auto_scraper.main(self)

        # 99. Espera dos minutos antes de volver a empezar
        time.sleep(120)


def main(self):
    t = threading.Thread(target=thread, args=(self,), daemon=True)
    self.log(action="[ SERVICIO ] CRON: Activado")
    t.start()
