import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


# local imports
from src.utils.webdriver import ChromeUtils
from src.utils.constants import HEADLESS


def browser(doc_num):

    chromedriver = ChromeUtils(headless=HEADLESS["osiptel"], window_size=(1920, 1080))
    webdriver = chromedriver.direct_driver()

    while True:

        webdriver.get("https://checatuslineas.osiptel.gob.pe/")
        time.sleep(2)

        drop = Select(webdriver.find_element(By.ID, "IdTipoDoc"))
        drop.select_by_value("1")

        webdriver.find_element(By.ID, "NumeroDocumento").send_keys(doc_num)
        time.sleep(1)

        btn = webdriver.find_element(By.ID, "btnBuscar")
        time.sleep(1)
        webdriver.execute_script("arguments[0].click();", btn)
        time.sleep(2)

        result = []
        for i in range(1, 6):
            parts = []
            for j in range(1, 4):
                xpath = f"/html/body/div[1]/div[2]/div/div/div/div/form/div[4]/div[2]/div/div/div[2]/div/table/tbody/tr[{i}]/td[{j}]"
                elem = webdriver.find_elements(By.XPATH, xpath)
                if elem and "No se encontraron" in elem[0].text:
                    webdriver.quit()
                    return []
                if elem:
                    parts.append(elem[0].text)
            if elem:
                result.append(parts)

        if result == [[], [], [], [], [], []]:
            webdriver.refresh()
        else:
            webdriver.quit()
            return result
