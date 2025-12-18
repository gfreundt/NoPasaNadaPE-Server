import time
import io
import copy
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoAlertPresentException
from src.utils.utils import use_truecaptcha
from func_timeout import func_set_timeout, exceptions
from src.utils.constants import SCRAPER_TIMEOUT


@func_set_timeout(SCRAPER_TIMEOUT["revtec"])
def browser_wrapper(placa, webdriver):
    try:
        return browser(placa, webdriver)
    except exceptions.FunctionTimedOut:
        return "Timeout"


def browser(placa, webdriver):

    url = "https://rec.mtc.gob.pe/Citv/ArConsultaCitv"

    intentos_captcha = 0
    while intentos_captcha < 5:

        # abrir url
        if webdriver.current_url != url:
            webdriver.get(url)
            time.sleep(2)

        # resolver captcha
        captcha_txt = ""
        while not captcha_txt:
            _captcha_img = webdriver.find_element(By.ID, "imgCaptcha")
            _img = io.BytesIO(_captcha_img.screenshot_as_png)
            captcha_txt = use_truecaptcha(_img)["result"]
            if not captcha_txt:
                return "Servicio Captcha Offline."

        # ingresar placa, texto de captcha y apretar boton buscar
        campo_placa = webdriver.find_element(By.ID, "texFiltro")
        campo_placa.clear()
        campo_placa.send_keys(placa)
        time.sleep(0.5)
        webdriver.find_element(By.ID, "texCaptcha").send_keys(captcha_txt)
        time.sleep(0.5)
        webdriver.find_element(By.ID, "btnBuscar").click()
        time.sleep(1)

        # ver si salio una alerta
        try:
            alert = webdriver.switch_to.alert

            # captcha equivocado - click y tratar con nuevo captcha
            if "no es" in alert.text:
                alert.accept()
                time.sleep(1)
                intentos_captcha += 1
                continue

            # no hay informacion de placa
            if "No se" in alert.text:
                alert.accept()
                return []

        # no hay alerta, capturar datos
        except NoAlertPresentException:
            pass

        # extraer datos de resultados de web
        response = []

        for pos in range(1, 9):
            response.append(webdriver.find_element(By.ID, f"Spv1_{pos}").text)

        if response[6] == "DESAPROBADO":
            response[5] = copy.deepcopy(response[4])
            response[7] = "VENCIDO"

        # proceso completo -- dejar la pagina lista para la siguiente placa
        webdriver.find_element(By.ID, "btnLimpiar").click()
        time.sleep(1)
        return response

    return "Exceso Reintentos Captcha"
