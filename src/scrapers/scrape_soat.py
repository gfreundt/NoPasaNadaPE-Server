from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import io
from src.utils.utils import use_truecaptcha
from func_timeout import func_set_timeout, exceptions
from src.utils.constants import SCRAPER_TIMEOUT


@func_set_timeout(SCRAPER_TIMEOUT["soat"])
def browser_wrapper(placa, webdriver):
    try:
        return browser(placa, webdriver)
    except exceptions.FunctionTimedOut:
        return "Timeout"


def browser(placa, webdriver):

    intentos_captcha = 0
    while intentos_captcha < 5:

        # abrir url
        url = "https://www.apeseg.org.pe/consultas-soat/"
        if webdriver.current_url != url:
            webdriver.get(url)
            time.sleep(2)

        # cambiar a frame
        webdriver.switch_to.frame(0)
        time.sleep(2)

        # extraer imagen de captcha y enviar a procesar
        _img = webdriver.find_element(By.CLASS_NAME, "captcha-img")
        captcha_file_like = io.BytesIO(_img.screenshot_as_png)
        captcha_txt = use_truecaptcha(captcha_file_like)["result"]
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
        WebDriverWait(webdriver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "/html/body/div/div/main/div/div/table/tbody/tr[1]/td")
            )
        )

        # busca datos, si no existen responder con error de scraper
        try:
            response = [
                webdriver.find_element(
                    By.XPATH,
                    f"/html/body/div/div/main/div/div/table/tbody/tr[{i}]/td",
                ).text.strip()
                for i in range(1, 13)
            ]
        except Exception:
            response = "@Sin Datos"

        # refrescar pagina para siguiente intento
        webdriver.back()
        time.sleep(2)
        webdriver.refresh()
        return response

    # error en respuesta
    return "Exceso Reintentos Captcha"
