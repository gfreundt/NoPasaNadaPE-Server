from selenium.webdriver.common.by import By
import time
import io
from src.utils.webdriver import ChromeUtils
from src.utils.utils import use_truecaptcha
from src.utils.constants import HEADLESS


def browser(doc_num):
    chromedriver = ChromeUtils(headless=HEADLESS["jneafil"], maximized=True)
    webdriver = chromedriver.direct_driver()

    webdriver.get("https://sroppublico.jne.gob.pe/Consulta/Afiliado")
    time.sleep(1.5)

    # ensure page loading with refresh
    webdriver.refresh()

    while True:

        _captcha_file_like = io.BytesIO(
            webdriver.find_element(
                By.XPATH, "/html/body/div[1]/form/div/div[2]/div/div/div/div[1]/img"
            ).screenshot_as_png
        )
        captcha_txt = use_truecaptcha(image=_captcha_file_like)["result"]
        if not captcha_txt:
            return "Servicio Captcha Offline."

        # enter data into fields and run
        webdriver.find_element(By.ID, "DNI").send_keys(doc_num)
        time.sleep(0.5)

        webdriver.find_element(
            By.XPATH, "/html/body/div[1]/form/div/div[2]/div/div/div/input"
        ).send_keys(captcha_txt)
        time.sleep(0.5)

        btn = webdriver.find_element(
            By.XPATH, "/html/body/div[1]/form/div/div[3]/button"
        )
        webdriver.execute_script("arguments[0].click();", btn)
        time.sleep(3)

        # if no error in captcha, continue
        _alert = webdriver.find_element(By.XPATH, "/html/body/div[1]/div[2]")
        if "vencido" not in _alert.text:
            break

        # otherwise, refresh captcha and restart loop
        btn = webdriver.find_element(
            By.XPATH, "/html/body/div[1]/form/div/div[2]/div/div/div/div[2]/i"
        )
        webdriver.execute_script("arguments[0].click();", btn)
        time.sleep(1)

    # grab "Historial de Afiliacion"
    _historial = webdriver.find_element(By.ID, "divMsjHistAfil")

    if "Ninguno" in _historial.text:
        webdriver.quit()
        return ""

    else:

        # grab image of JNE affiliation and save in data folder
        _imgbytes = webdriver.find_element(
            By.XPATH, "/html/body/div[1]/div[2]/div"
        ).screenshot_as_base64

        # close webdrive
        webdriver.quit()
        return _imgbytes
