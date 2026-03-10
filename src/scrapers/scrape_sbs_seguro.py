import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


def browser(datos, webdriver):

    placa = datos["Placa"]

    # abrir url
    url = "https://servicios.sbs.gob.pe/reportesoat/"
    webdriver.set_page_load_timeout(60)
    try:
        webdriver.get(url)
    except TimeoutException:
        webdriver.execute_script("window.stop();")
    time.sleep(2)

    placa_field = webdriver.find_element(By.ID, "ctl00_MainBodyContent_txtPlaca")
    btn_seguro = webdriver.find_element(
        By.ID, "ctl00_MainBodyContent_rblOpcionesSeguros_1"
    )
    btn_consultar = webdriver.find_element(
        By.ID, "ctl00_MainBodyContent_btnIngresarPla"
    )

    placa_field.send_keys(placa)
    time.sleep(1)
    webdriver.execute_script("arguments[0].click();", btn_seguro)
    time.sleep(1)
    webdriver.execute_script("arguments[0].click();", btn_consultar)
    time.sleep(1)

    body = "/html/body/div[4]/div/div/div/form/div[3]/div/div[3]/div/div/div/div/table[2]/tbody"
    if not webdriver.find_elements(By.XPATH, f"{body}[1]/tr/td[1]"):
        return []

    response = []
    for i in range(1, 10):
        print("********", i)
        x = webdriver.find_element(By.XPATH, f"{body}[1]/tr/td[{i}]") or ""
        response.append(x.text)
        print("++++++++++", x.text)

    print("-------------------")
    print(response)

    return [response]


def main():
    from src.utils.webdriver import ChromeUtils

    chromedriver = ChromeUtils()
    webdriver = chromedriver.proxy_driver(residential=False, headless=True)

    datos = {"Placa": "AMQ073"}

    f = browser(datos, webdriver)

    print(f)
