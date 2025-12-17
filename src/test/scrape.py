import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import uuid


def config():

    service = Service("chromedriver.exe", log_path=os.devnull)
    options = Options()

    options.add_argument("--incognito")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    # options.add_argument("--disable-notifications")
    # options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.7444.176 Safari/537.36"
    )

    return service, options


def proxy_driver(self, residential=False):
    # build a new session id to force a different IP
    session = uuid.uuid4().hex[:8]
    raw_username = (
        f"{PROXY_RES_USERNAME if residential else PROXY_DC_USERNAME}{session}"
    )
    password = PROXY_RES_PASSWORD if residential else PROXY_DC_PASSWORD
    _seleniumwire_options = {
        "proxy": {
            "http": f"http://{raw_username}:{password}@{PROXY_HOST}:{PROXY_PORT}",
            "https": f"http://{raw_username}:{password}@{PROXY_HOST}:{PROXY_PORT}",
        }
    }
    self.options.add_argument("--ignore-certificate-errors")

    return webdriver_wire.Chrome(
        service=self.service,
        seleniumwire_options=_seleniumwire_options,
        options=self.options,
    )


def direct_driver(service, options):

    return webdriver.Chrome(
        service=service,
        options=options,
    )


def browser(dni):

    service, options = config()
    webdriver = direct_driver(service, options)

    while True:

        webdriver.get("https://checatuslineas.osiptel.gob.pe/")
        time.sleep(2)

        drop = Select(webdriver.find_element(By.ID, "IdTipoDoc"))
        drop.select_by_value("1")

        webdriver.find_element(By.ID, "NumeroDocumento").send_keys(dni)
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


print(browser(dni="09877145"))
