import time
import io
import copy
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoAlertPresentException
from src.utils.utils import use_truecaptcha
from func_timeout import func_set_timeout, exceptions
from src.utils.constants import SCRAPER_TIMEOUT


@func_set_timeout(SCRAPER_TIMEOUT["calmul"])
def browser_wrapper(placa, webdriver):
    try:
        return browser(placa, webdriver)
    except exceptions.FunctionTimedOut:
        return "Timeout"


def browser(placa, webdriver):

    url = "https://pagopapeletascallao.pe/"

    intentos_captcha = 0
    while intentos_captcha < 5:

        # abrir url
        if webdriver.current_url != url:
            webdriver.get(url)
            time.sleep(2)

        # resolver captcha
        captcha_txt = ""
        while not captcha_txt:
            _captcha_img = webdriver.find_element(
                By.XPATH, "/html/body/div[3]/div[2]/div[3]/p/img"
            )
            _img = io.BytesIO(_captcha_img.screenshot_as_png)
            captcha_txt = use_truecaptcha(_img)["result"]
            if not captcha_txt:
                return "Servicio Captcha Offline."

        # ingresar placa, texto de captcha y apretar boton buscar
        campo_placa = webdriver.find_element(By.ID, "valor_busqueda")
        campo_placa.clear()
        campo_placa.send_keys(placa)
        time.sleep(0.5)
        webdriver.find_element(By.ID, "captcha").send_keys(captcha_txt)
        time.sleep(0.5)
        webdriver.find_element(By.ID, "idBuscar").click()
        time.sleep(1)

        # mensaje: captcha equivocado
        msg = webdriver.find_elements(By.XPATH, "/html/body/div[3]/div[2]/div[6]/p")
        if msg and "seguridad" in msg[0].text:
            time.sleep(1)
            intentos_captcha += 1
            continue

        # mensaje: no hay data de placa
        msg = webdriver.find_elements(By.XPATH, "/html/body/div[3]/div[3]/p")
        if msg and "mostrar" in msg[0].text:
            return []

        # extraer datos de resultados de web
        filas = webdriver.find_elements(
            By.XPATH, "/html/body/div[3]/div[3]/div/div[2]/div/table/tbody/tr"
        )

        response = []
        for row_element in filas:
            cells = row_element.find_elements(By.XPATH, "./td")[1:7]
            row_data = [cell.text for cell in cells]
            response.append(row_data)

        # proceso completo -- pagina ya queda lista para el siguiente registro
        time.sleep(1)
        return response

    return "Exceso Reintentos Captcha"
