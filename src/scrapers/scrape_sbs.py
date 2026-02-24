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
    time.sleep(3)

    tbody = webdriver.find_element(By.CSS_SELECTOR, "#listSoatPlacaVeh tbody")
    first_row = tbody.find_elements(By.TAG_NAME, "tr")[0]
    tds = first_row.find_elements(By.TAG_NAME, "td")

    return [td.text.strip() for td in tds]
