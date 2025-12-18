import os
import io
import base64

# import pyautogui
import time
from func_timeout import func_set_timeout, exceptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from src.utils.utils import use_truecaptcha
from src.utils.constants import NETWORK_PATH, SCRAPER_TIMEOUT


@func_set_timeout(SCRAPER_TIMEOUT["revtec"])
def browser_wrapper(doc_num, webdriver, lock):
    try:
        return browser(doc_num, webdriver, lock)
    except exceptions.FunctionTimedOut:
        return "Timeout"


def browser(doc_num, webdriver, lock):

    url = "https://recordconductor.mtc.gob.pe/"

    intentos_captcha = 0
    while intentos_captcha < 5:

        # abrir url
        if webdriver.current_url != url:
            webdriver.get(url)
            time.sleep(2)

        try:
            # extraer texto de captcha
            _captcha_file_like = io.BytesIO(
                webdriver.find_element(By.ID, "idxcaptcha").screenshot_as_png
            )
            captcha_txt = use_truecaptcha(_captcha_file_like)["result"]
            if not captcha_txt:
                return "Servicio Captcha Offline."

            # ingresar en formulario y apretar buscar
            try:
                t = WebDriverWait(webdriver, 7).until(
                    EC.visibility_of_element_located((By.ID, "txtNroDocumento"))
                )
                t.send_keys(doc_num)
            except TimeoutException:
                return "Campo no puede interactuar"

            webdriver.find_element(By.ID, "idCaptcha").send_keys(captcha_txt)
            time.sleep(1)

            # esperar a que boton se pueda presionar
            try:
                b = WebDriverWait(webdriver, 7).until(
                    EC.element_to_be_clickable((By.ID, "BtnBuscar"))
                )
                b.click()
            except TimeoutException:
                return "Boton no se puede presionar"

            time.sleep(3)

            # obtener mensaje de alerta (si hay)
            _alerta = webdriver.find_elements(
                By.XPATH, "/html/body/div[5]/div/div/div[1]/label"
            )

            # mensaje de alerta: captcha equivocado
            if _alerta and "ingresado" in _alerta[0].text:
                # refrescar captcha (presionar boton) para siguiente iteracion
                webdriver.refresh()
                intentos_captcha += 1
                time.sleep(3)
                continue

            # mensaje de alerta: no hay informacion de la persona
            elif _alerta and "PERSONA" in _alerta[0].text:
                return []

        except ValueError:
            # no carga imagen de captcha, refrescar pagina y volver a intentar
            webdriver.refresh()
            intentos_captcha += 1
            time.sleep(3)
            return "No Carga Captcha"

        # inicia extraccion de datos

        # parametros necesarios para que no abra ventana de dialogo de "Guardar Como..."
        webdriver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": os.path.join(NETWORK_PATH, "static"),
            },
        )

        # apretar boton que lleva a bajar archivo
        b = webdriver.find_elements(By.ID, "btnprint")
        with lock:
            try:
                webdriver.execute_script("arguments[0].click();", b[0])
                time.sleep(2)

            except Exception:
                webdriver.refresh()
                return "@No Hay Boton Download"

            # si ha bajado un archivo copia porque no se borro el anterior generar error
            if os.path.isfile(
                os.path.join(NETWORK_PATH, "static", "RECORD DE CONDUCTOR (2).pdf")
            ):
                return "Multiples archivos de PDF."

            # esperar un tiempo hasta que baje el archivo
            start_time = time.time()
            _file = os.path.join(NETWORK_PATH, "static", "RECORD DE CONDUCTOR.pdf")
            while time.time() - start_time < 12:

                if os.path.isfile(_file):

                    # refrescar captcha (presionar boton) para siguiente iteracion
                    b = webdriver.find_element(By.ID, "idxRefreshCapcha")
                    webdriver.execute_script("arguments[0].click();", b)

                    # borrar download y devolver la imagen en bytes
                    with open(_file, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                    os.remove(_file)
                    return data

                time.sleep(1)

            # si no se encontro imagen, retornar error
            return "@No Se Puedo Bajar Archivo"

    # demasiados intentos de captcha errados consecutivos
    return "Excede Intentos de Captcha"
