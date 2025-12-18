import base64
import time
import requests

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from func_timeout import func_set_timeout, exceptions

from src.utils.constants import SCRAPER_TIMEOUT
from security.keys import TWOCAPTCHA_API_KEY


@func_set_timeout(SCRAPER_TIMEOUT["satmuls"])
def browser_wrapper(doc_num, webdriver):
    try:
        return browser(doc_num, webdriver)
    except exceptions.FunctionTimedOut:
        return "Timeout"


def browser(placa, webdriver):

    # abrir url
    url_inicial = "https://www.sat.gob.pe/WebSitev8/IncioOV2.aspx"
    webdriver.get(url_inicial)

    # extraer codigo de sesion y navegar a url final
    url_final = f"""https://www.sat.gob.pe/VirtualSAT/modulos/papeletas.aspx?
                    tri=T&mysession={webdriver.current_url.split("=")[-1]}"""
    webdriver.get(url_final)
    time.sleep(1)

    # resetar el boton de opciones
    drop = Select(webdriver.find_element(By.ID, "tipoBusquedaPapeletas"))
    drop.select_by_value("busqLicencia")
    time.sleep(0.5)
    drop.select_by_value("busqPlaca")

    # ingresar placa
    campo = webdriver.find_element(By.ID, "ctl00_cplPrincipal_txtPlaca")
    campo.send_keys(placa)
    time.sleep(0.5)

    # resolver recaptcha
    token = solve_recaptcha(webdriver, webdriver.current_url)
    if not token:
        return "Problemas con Resolucion de Recaptcha"

    # inyectar token en 'g-recaptcha-response'
    webdriver.execute_script(
        """
        document.getElementById('g-recaptcha-response').style.display = 'block';
        document.getElementById('g-recaptcha-response').value = arguments[0];
        document.getElementById('g-recaptcha-response').dispatchEvent(new Event('input'));
        document.getElementById('g-recaptcha-response').dispatchEvent(new Event('change'));
    """,
        token,
    )
    time.sleep(1)

    # click en continuar
    try:
        webdriver.find_element(By.ID, "ctl00_cplPrincipal_CaptchaContinue").click()
    except Exception:
        return "No Se Pudo Hacer Click en Boton de Continuar"

    # Wait for results to load
    time.sleep(3)

    # respuesta correcta sin papeletas
    empty_msg = webdriver.find_elements(By.ID, "ctl00_cplPrincipal_lblMensajeVacio")
    if empty_msg and "No se encontraron" in empty_msg[0].text:
        # regresar a "consulta de papeletas" para siguiente iteracion y devolver en blanco
        regresar_inicio(webdriver, url_final)
        return []

    # respuesta correcta con papeletas
    n = 2
    responses = []

    # extrae todas las filas de multas
    while xpath_generator(webdriver, n, 1):

        # extraer campos (excepto fila 12)
        resp = [
            xpath_generator(webdriver, n, k + 2)[0].text for k in range(14) if k != 10
        ]

        # url de potenciales imagenes
        ids = (
            "ctl00_cplPrincipal_grdEstadoCuenta_ctl02_lnkImagen",
            "ctl00_cplPrincipal_grdEstadoCuenta_ctl02_lnkDocumento",
        )

        urls = []
        for id in ids:
            w = webdriver.find_elements(By.ID, id)
            urls.append(w[0].get_attribute("href") if w else "")

        # descargar imagenes
        ids = ("imgPapel", "imgPapeleta")
        for id, url in zip(ids, urls):
            if url:
                webdriver.get(url)
                time.sleep(3)
                img = webdriver.find_elements(By.ID, id)
                if img:
                    img_url = img[0].get_attribute("src")
                    response = requests.get(img_url, stream=True)
                    resp.append(base64.b64encode(response.content).decode("utf-8"))
                else:
                    resp.append("")
            else:
                resp.append("")

        responses.append(resp)
        n += 1

    # regresar a "consulta de papeletas" para siguiente iteracion y devolver respuestas
    regresar_inicio(webdriver, url_final)
    return responses


def xpath_generator(webdriver, row, col):
    return webdriver.find_elements(
        By.XPATH,
        f"/html/body/form/div[3]/section/div/div/div[2]/div[8]/div/div/div[1]/div/div/table/tbody/tr[{row}]/td[{col}]",
    )


def regresar_inicio(webdriver, url_final):
    try:
        webdriver.find_element(By.ID, "menuOption10").click()
    except NoSuchElementException:
        webdriver.get(url_final)
        time.sleep(1)


def solve_recaptcha(webdriver, page_url):
    """
    Extracts the sitekey, sends solve request to 2captcha,
    polls for result, and returns the token.
    """

    # Find recaptcha sitekey
    sitekey = webdriver.find_element(By.CSS_SELECTOR, ".g-recaptcha").get_attribute(
        "data-sitekey"
    )

    # Send solve request
    try:
        resp = requests.post(
            "http://2captcha.com/in.php",
            data={
                "key": TWOCAPTCHA_API_KEY,
                "method": "userrecaptcha",
                "googlekey": sitekey,
                "pageurl": page_url,
            },
        ).text

        if "OK|" not in resp:
            return False

        task_id = resp.split("|")[1]

        # Poll until solved
        token = None
        for _ in range(48):  # ~4 minutes max
            time.sleep(5)
            check = requests.get(
                "http://2captcha.com/res.php",
                params={"key": TWOCAPTCHA_API_KEY, "action": "get", "id": task_id},
            ).text

            if check == "CAPCHA_NOT_READY":
                continue

            if "OK|" in check:
                token = check.split("|")[1]
                break

            return False

        if not token:
            return False

        return token

    except Exception:
        return False
