import time
from selenium.webdriver.common.by import By
import os, atexit, shutil, tempfile
import platform
from selenium import webdriver as wd
from selenium.webdriver.chrome.options import Options as WebDriverOptions
from selenium.webdriver.chrome.service import Service


def init_driver(**kwargs):

    user_data_dir = tempfile.mkdtemp(prefix="selenium-profile-")
    atexit.register(lambda: shutil.rmtree(user_data_dir, ignore_errors=True))

    """Returns a ChromeDriver object with commonly used parameters allowing for some optional settings"""

    # set defaults that can be overridden by passed parameters
    parameters = {
        "incognito": False,
        "headless": False,
        "window_size": False,
        "load_profile": False,
        "verbose": True,
        "no_driver_update": False,
        "maximized": False,
    } | kwargs

    options = WebDriverOptions()

    # configurable options
    # options.add_argument(f"--user-data-dir={user_data_dir}")
    if parameters["incognito"]:
        options.add_argument("--incognito")
    if parameters["headless"]:
        options.add_argument("--headless=new")
    if parameters["window_size"]:
        options.add_argument(
            f"--window-size={parameters['window_size'][0]},{parameters['window_size'][1]}"
        )

    # fixed options

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--silent")
    options.add_argument("--disable-notifications")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    _path = (
        os.path.join("src", "chromedriver.exe")
        if "Windows" in platform.uname().system
        else "/usr/local/bin/chromedriver"
    )

    return wd.Chrome(service=Service(_path, log_path=os.devnull), options=options)


doc_num = "10612549"

webdriver = init_driver(headless=False, verbose=False, maximize=True)
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
    print("Naka")
# get information
btn = webdriver.find_element(By.XPATH, "/html/body/div/div[2]/div/div[3]/div[2]/a/span")
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
    print(response)
