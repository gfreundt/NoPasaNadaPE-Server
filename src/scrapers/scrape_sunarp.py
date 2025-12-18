from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, re
import requests

from func_timeout import func_set_timeout, exceptions
from src.utils.constants import SCRAPER_TIMEOUT


@func_set_timeout(SCRAPER_TIMEOUT["sunarps"])
def browser_wrapper(placa, webdriver):
    try:
        return browser(placa, webdriver)
    except exceptions.FunctionTimedOut:
        return "Timeout"


def browser(placa, webdriver):

    url_inicio = "https://www.gob.pe/sunarp"
    url_final = "https://consultavehicular.sunarp.gob.pe/consulta-vehicular"

    if webdriver.current_url != url_final:
        # abrir este url primero para evitar limite de consultas
        webdriver.get(url_inicio)
        time.sleep(2)

        # abrir url definitivo
        webdriver.get(url_final)
        time.sleep(4)

    # resolver cloudfare turnstile (o pasar si ya esta chequeado)
    solve_cloudflare_turnstile(webdriver, url_final, TWOCAPTCHA_API_KEY)

    # x = webdriver.find_elements(By.XPATH, "/html/body//div/div/div[1]/div/label/input")
    # if x:
    #     webdriver.execute_script("arguments[0].click();", x[0])
    #     time.sleep(2)

    # ingresar datos de placa
    webdriver.find_element(By.ID, "nroPlaca").send_keys(placa)
    time.sleep(0.5)

    # click on "Realizar Busqueda"
    btn = webdriver.find_element(
        By.XPATH,
        "/html/body/app-root/nz-content/div/app-inicio/app-vehicular/nz-layout/nz-content/div/nz-card/div/app-form-datos-consulta/div/form/fieldset/nz-form-item[3]/nz-form-control/div/div/div/button",
    )
    webdriver.execute_script("arguments[0].click();", btn)
    time.sleep(1)

    _alerta = webdriver.find_elements(By.ID, "swal2-html-container")

    if _alerta and "error" in _alerta[0].text:
        btn = webdriver.find_element(By.XPATH, "/html/body/div/div/div[6]/button[1]")
        webdriver.execute_script("arguments[0].click();", btn)
        return "@Error de pagina."

    # esperar hasta 10 segundos a que termine de cargar la imagen
    time_start = time.perf_counter()
    _card_image = None
    while not _card_image and time.perf_counter() - time_start < 10:
        _card_image = webdriver.find_elements(
            By.XPATH,
            "/html/body/app-root/nz-content/div/app-inicio/app-vehicular/nz-layout/nz-content/div/nz-card/div/app-form-datos-consulta/div/img",
        )
        time.sleep(0.5)

    # error que luego de 10 segundos no cargo imagen
    if not _card_image:
        return "@No Carga Imagen."

    # solicitud correcta, no hay datos
    e = webdriver.find_elements(By.ID, "swal2-html-container")
    if e and "nuevamente" in e[0].text:
        webdriver.refresh()
        return []

    # solicitud correcta, si hay datos, regresar imagen como bytes
    image_bytes = _card_image[0].screenshot_as_base64

    # presionar "volver" para siguiente iteracion (temporalmente refrescar pagina)
    time.sleep(1)
    webdriver.refresh()
    # b = webdriver.find_element(
    #     By.CSS_SELECTOR, "ant-btn btn-sunarp-green ant-btn-primary ant-btn-lg"
    # )
    # webdriver.execute_script("arguments[0].click();", b)
    return image_bytes


def solve_cloudflare_turnstile(webdriver, page_url, TWOCAPTCHA_API_KEY):
    solved_input = WebDriverWait(webdriver, 10).until(
        EC.presence_of_element_located((By.NAME, "cf-turnstile-response"))
    )
    existing_token = solved_input.get_attribute("value")
    if existing_token:
        print(
            "Turnstile challenge already solved by the browser! Using existing token."
        )
        # If the token is already present, the WebDriver can proceed without 2Captcha.
        return existing_token

    sitekey = None
    IFRAME_SELECTOR = 'iframe[id^="cf-chl-widget-"]'

    iframe_element = WebDriverWait(webdriver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, IFRAME_SELECTOR))
    )
    iframe_src = iframe_element.get_attribute("src")

    match = re.search(r"/(0x[a-zA-Z0-9]+)/light/", iframe_src)

    if match:
        sitekey = match.group(1)
    else:
        print(f"Error: Could not find sitekey pattern in iframe src: {iframe_src}")

    if not sitekey:
        print("Error: Extracted element did not contain a valid sitekey.")
        return False

    if not sitekey:
        print("Error: Could not extract the Turnstile data-sitekey.")
        return False

    resp = requests.post(
        "http://2captcha.com/in.php",
        data={
            "key": TWOCAPTCHA_API_KEY,
            "method": "turnstile",
            "sitekey": sitekey,
            "pageurl": page_url,
        },
    ).text

    if "OK|" not in resp:
        print(f"Error submitting CAPTCHA to 2Captcha: {resp}")
        return False

    task_id = resp.split("|")[1]
    print(f"Successfully submitted task. Task ID: {task_id}")

    # --- 4. Poll until solved ---
    token = None
    for attempt in range(48):
        time.sleep(5)
        check = requests.get(
            "http://2captcha.com/res.php",
            params={"key": TWOCAPTCHA_API_KEY, "action": "get", "id": task_id},
        ).text

        if check == "CAPCHA_NOT_READY":
            continue

        if "OK|" in check:
            token = check.split("|")[1]
            print("CAPTCHA solved successfully by 2Captcha!")
            break

        print(f"Error while polling for result: {check}")
        return False

    if not token:
        print("Failed to get CAPTCHA token within the timeout.")
        return False

    # --- 5. Inject the token into the page (Crucial Step) ---
    # The token must be injected into the hidden input field named 'cf-turnstile-response'
    # If the element is not there, we have to create it.
    webdriver.execute_script(
        f'document.getElementsByName("cf-turnstile-response")[0].value = "{token}";'
    )
    print("Token injected into the 'cf-turnstile-response' field.")

    # In case the site uses a submit button, you might need to click it again
    # to trigger the final check after the token is injected.

    return token
