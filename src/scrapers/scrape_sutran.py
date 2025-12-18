from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
from func_timeout import func_set_timeout, exceptions
from src.utils.constants import SCRAPER_TIMEOUT


@func_set_timeout(SCRAPER_TIMEOUT["sutrans"])
def browser_wrapper(placa, webdriver):
    try:
        return browser(placa, webdriver)
    except exceptions.FunctionTimedOut:
        return "Timeout"


def browser(placa, webdriver):

    url = "https://www.sutran.gob.pe/consultas/record-de-infracciones/record-de-infracciones/"
    webdriver.get(url)
    time.sleep(2)

    if not revisar_carga_pagina(webdriver):
        return "Error Cargando Pagina"

    while True:
        # capture captcha image from frame name
        _iframe = webdriver.find_element(By.CSS_SELECTOR, "iframe")
        webdriver.switch_to.frame(_iframe)
        captcha_txt = (
            webdriver.find_element(By.ID, "iimage").get_attribute("src").split("=")[-1]
        )
        captcha_txt = captcha_txt.replace("%C3%91", "Ñ")

        # enter data into fields and run
        webdriver.find_element(By.ID, "txtPlaca").send_keys(placa)
        time.sleep(0.2)
        elements = (
            webdriver.find_elements(By.ID, "TxtCodImagen"),
            webdriver.find_elements(By.ID, "BtnBuscar"),
        )
        if not elements[0] or not elements[1]:
            webdriver.refresh()
            continue
        else:
            elements[0][0].send_keys(captcha_txt)
            time.sleep(0.2)
            elements[1][0].click()
        time.sleep(0.5)

        # if no text response, restart loop
        elements = webdriver.find_elements(By.ID, "LblMensaje")
        if elements:
            _alerta = webdriver.find_element(By.ID, "LblMensaje").text
        else:
            webdriver.refresh()
            continue

        # if no pendings, return empty dictionary
        if "pendientes" in _alerta:
            return []
        else:
            break

    # get responses and package into list of dictionaries
    response = []
    pos1 = 2
    _xpath_partial = "/html/body/form/div[3]/div[3]/div/table/tbody/"

    # loop on all documentos
    while webdriver.find_elements(By.XPATH, _xpath_partial + f"tr[{pos1}]/td[1]"):
        item = []

        # loop on all items in documento
        for pos2 in range(1, 6):
            item.append(
                webdriver.find_element(
                    By.XPATH,
                    _xpath_partial + f"tr[{pos1}]/td[{pos2}]",
                ).text
            )

        # append dictionary to list
        response.append(item)
        pos1 += 1

    # last item is garbage, remove from response
    response.pop()

    # succesful, return list of dictionaries
    return response


def revisar_carga_pagina(webdriver):
    intentos_carga = 0
    while intentos_carga < 3:
        try:
            WebDriverWait(webdriver, 5).until(
                EC.presence_of_element_located((By.ID, "post-1120"))
            )
            return True
        except TimeoutException:
            intentos_carga += 1
            webdriver.refresh()

    return False
