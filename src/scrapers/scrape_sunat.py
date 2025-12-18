import time
from selenium.webdriver.common.by import By

# local imports
from src.utils.webdriver import ChromeUtils
from src.utils.constants import HEADLESS


def browser(doc_tipo, doc_num):

    chromedriver = ChromeUtils(headless=HEADLESS["sunat"], verbose=False, maximize=True)
    webdriver = chromedriver.direct_driver()

    webdriver.get(
        "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp"
    )
    time.sleep(2)

    # press by documento, enter documento and click
    btn = webdriver.find_element(By.ID, "btnPorDocumento")
    webdriver.execute_script("arguments[0].click();", btn)
    time.sleep(1)

    webdriver.find_element(By.ID, "txtNumeroDocumento").send_keys(doc_num)

    btn = webdriver.find_element(By.ID, "btnAceptar")
    webdriver.execute_script("arguments[0].click();", btn)
    time.sleep(2)

    # check for no information on dni
    if "El Sistema RUC NO REGISTRA" in webdriver.page_source:
        webdriver.quit()
        return -1

    # get information
    btn = webdriver.find_element(
        By.XPATH, "/html/body/div/div[2]/div/div[3]/div[2]/a/span"
    )
    webdriver.execute_script("arguments[0].click();", btn)
    time.sleep(2)

    response = []
    for i in range(1, 9):
        d = webdriver.find_elements(
            By.XPATH, f"/html/body/div/div[2]/div/div[3]/div[2]/div[{i}]/div/div[2]"
        )
        if d:
            _r = d[0].text.replace("\n", " - ")
            response.append(_r)
    e = webdriver.find_elements(
        By.XPATH, "/html/body/div/div[2]/div/div[3]/div[2]/div[5]/div/div[4]/p"
    )

    if e:
        response.append(e[0].text)

    btn = webdriver.find_element(By.XPATH, "/html/body/div/div[2]/div/div[2]/button")
    webdriver.execute_script("arguments[0].click();", btn)

    if len(response) == 9:
        webdriver.quit()
        return response
