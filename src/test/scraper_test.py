import time
from selenium.webdriver.common.by import By
import platform
from selenium import webdriver as wd
from selenium.webdriver.chrome.options import Options as WebDriverOptions
from selenium.webdriver.chrome.service import Service
import os, platform, socket
from uuid import uuid4


def _free_port():
    s = socket.socket()
    s.bind(("", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def init_driver(**kwargs):
    # defaults
    params = {
        "incognito": False,
        "headless": False,
        "window_size": False,
        "verbose": True,
        "maximized": False,
        # only set this True if you *really* need a persistent profile
        "use_custom_profile": False,
        "custom_profile_dir": None,  # e.g., "/home/you/chrome-profiles/mybot"
    } | kwargs

    options = WebDriverOptions()

    # IMPORTANT: do NOT set --user-data-dir by default
    if params["use_custom_profile"]:
        # create a unique subprofile to avoid locks
        base = params["custom_profile_dir"] or os.path.expanduser(
            "~/.cache/selenium-profiles"
        )
        os.makedirs(base, exist_ok=True)
        sub = os.path.join(base, f"Profile-{uuid4().hex}")
        os.makedirs(sub, exist_ok=True)
        options.add_argument(f"--user-data-dir={sub}")
        options.add_argument("--profile-directory=Default")

    if params["incognito"]:
        options.add_argument("--incognito")
    if params["headless"]:
        options.add_argument("--headless=new")
    if params["window_size"]:
        w, h = params["window_size"]
        options.add_argument(f"--window-size={w},{h}")

    # stability/safety flags
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-dev-shm-usage")
    # if you ever run as root (CI/systemd/docker), also add:
    # options.add_argument("--no-sandbox")

    # avoid devtools port collisions
    options.add_argument(f"--remote-debugging-port={_free_port()}")

    # don’t lie about Chrome’s version; remove the hard-coded UA you had
    # If you really need a UA, make sure it matches your installed Chrome major.

    driver_path = (
        os.path.join("src", "chromedriver.exe")
        if "Windows" in platform.uname().system
        else "/usr/local/bin/chromedriver"
    )
    driver = wd.Chrome(service=Service(driver_path), options=options)

    if params["maximized"]:
        try:
            driver.maximize_window()
        except Exception:
            pass
    return driver


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
