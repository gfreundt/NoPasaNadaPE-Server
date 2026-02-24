from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
import time
import io

from src.utils.utils import use_truecaptcha


def browser(datos, webdriver):

    placa = datos["Placa"]

    intentos_captcha = 0
    while intentos_captcha < 5:
        # abrir url
        webdriver.set_page_load_timeout(45)  # seconds
        url = "https://www.apeseg.org.pe/consultas-soat/"

        try:
            webdriver.get(url)
            time.sleep(2)
        except TimeoutException:
            webdriver.execute_script("window.stop();")
            time.sleep(2)
            _btn = webdriver.find_elements(
                By.ID, "/html/body/div/div/main/div/form/button"
            )
            if not _btn:
                webdriver.refresh()
                time.sleep(2)
                continue

        # cambiar a frame
        webdriver.switch_to.frame(0)
        time.sleep(2)

        # extraer imagen de captcha y enviar a procesar
        _img = webdriver.find_element(By.CLASS_NAME, "captcha-img")
        captcha_file_like = io.BytesIO(_img.screenshot_as_png)
        captcha_txt = use_truecaptcha(captcha_file_like).get("result")
        if not captcha_txt:
            return "Servicio Captcha Offline."

        # ingresar placa en campo
        webdriver.find_element(By.ID, "placa").send_keys(placa)

        # ingresar captcha en campo
        webdriver.find_element(By.ID, "captcha").send_keys(captcha_txt)
        # apretar "Consultar"
        but = webdriver.find_element(
            By.XPATH, "/html/body/div/div/main/div/form/button"
        )
        webdriver.execute_script("arguments[0].click();", but)
        time.sleep(3)
        # detectar captcha incorrecto, intentar otra vez
        msg = webdriver.find_elements(By.XPATH, "/html/body/div/div/main/div/form/p")
        if msg and "incorrecto" in msg[0].text:
            intentos_captcha += 1
            webdriver.refresh()
            time.sleep(2)
            continue
        # sin respuesta
        msg = webdriver.find_elements(By.XPATH, "/html/body/div/div/main/div/div/h2")
        if msg and "la placa solicitada" in msg[0].text:
            webdriver.quit()
            return []
        # extraer data de respuesta (espera hasta 10 segundos que aparezca)

        # busca datos, si no existen responder con error de scraper
        try:
            WebDriverWait(webdriver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "/html/body/div/div/main/div/div/table/tbody/tr[1]/td")
                )
            )
            response = [
                webdriver.find_element(
                    By.XPATH,
                    f"/html/body/div/div/main/div/div/table/tbody/tr[{i}]/td",
                ).text.strip()
                for i in range(1, 13)
            ]
        except (
            TimeoutException,
            StaleElementReferenceException,
            NoSuchElementException,
        ):
            response = "@Sin Datos"

        return [response]

    # error en respuesta
    return "Exceso Reintentos Captcha"
