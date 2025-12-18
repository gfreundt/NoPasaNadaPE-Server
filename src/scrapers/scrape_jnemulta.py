from selenium.webdriver.common.by import By
import time
import io
from src.utils.webdriver import ChromeUtils
from src.utils.utils import use_truecaptcha
from src.utils.constants import HEADLESS


def browser(doc_num):
    chromedriver = ChromeUtils(headless=HEADLESS["jnemulta"])
    webdriver = chromedriver.direct_driver()

    webdriver.get("https://multas.jne.gob.pe/login")
    time.sleep(1.5)

    # ensure page loading with refresh
    webdriver.refresh()

    while True:

        _captcha_file_like = io.BytesIO(
            webdriver.find_element(
                By.XPATH,
                "/html/body/div/div[2]/div/app-root/app-principal/div[1]/div[1]/div/div/div/form/app-captcha/div/div[2]/div[1]/div/img",
            ).screenshot_as_png
        )

        # get captcha text and validate
        captcha_txt = use_truecaptcha(_captcha_file_like)["result"]
        if not captcha_txt:
            return "Servicio Captcha Offline."
        if len(captcha_txt) != 6:
            webdriver.refresh()
            time.sleep(3)
            continue

        # enter DNI data
        webdriver.find_element(
            By.XPATH,
            "/html/body/div/div[2]/div/app-root/app-principal/div[1]/div[1]/div/div/div/form/label[1]/input",
        ).send_keys(doc_num)
        time.sleep(1)

        # enter solved captcha
        webdriver.find_element(
            By.XPATH,
            "/html/body/div/div[2]/div/app-root/app-principal/div[1]/div[1]/div/div/div/form/app-captcha/div/div[1]/input",
        ).send_keys(captcha_txt)
        time.sleep(1)

        # click on "acepto terminos y condiciones"
        btn = webdriver.find_element(By.ID, "ckbtermino")
        webdriver.execute_script("arguments[0].click();", btn)
        time.sleep(1)

        # click on Aceptar
        btn = webdriver.find_element(
            By.XPATH,
            "/html/body/div[1]/div[2]/div/app-root/app-principal/div[2]/div/div/div[3]/button[1]",
        )
        webdriver.execute_script("arguments[0].click();", btn)
        time.sleep(1)

        # click on Consultar
        btn = webdriver.find_element(By.ID, "btnConsultar")
        webdriver.execute_script("arguments[0].click();", btn)
        time.sleep(2)

        # check if error on captcha
        _btn = webdriver.find_elements(
            By.XPATH, "/html/body/div[2]/div/div[6]/button[1]"
        )
        if _btn:
            _btn[0].click()
            time.sleep(1)
            webdriver.refresh()
            time.sleep(3)
            continue

        # check if no multas
        _p = webdriver.find_elements(
            By.XPATH,
            "/html/body/div/div[2]/div/app-root/app-multas/div/div/div[1]/div[2]/img",
        )

        if _p and "imgsinmultas" in _p[0].get_attribute("class"):
            webdriver.quit()
            return []
        else:
            break

    response = ["Encontramos!"]

    # succesful, return list
    webdriver.quit()
    return response
