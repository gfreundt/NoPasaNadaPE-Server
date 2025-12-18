import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.utils.constants import MTC_CAPTCHAS, SCRAPER_TIMEOUT
from func_timeout import func_set_timeout, exceptions


@func_set_timeout(SCRAPER_TIMEOUT["brevetes"])
def browser_wrapper(doc_num, webdriver):
    try:
        return browser(doc_num, webdriver)
    except exceptions.FunctionTimedOut:
        return "Timeout"


def browser(doc_num, webdriver):

    # abrir url
    url = "https://licencias.mtc.gob.pe/#/index"
    if webdriver.current_url != url:
        webdriver.get(url)
        time.sleep(2)
    else:
        webdriver.refresh()

    # esperar a que boton de cerrar pop-up se active (max 15 segundos)
    popup_btn, k = [], 0
    while not popup_btn and k < 30:
        popup_btn = webdriver.find_elements(
            By.XPATH,
            "/html/body/div/div[2]/div/mat-dialog-container/app-popupanuncio/div/mat-dialog-actions/button",
        )
        time.sleep(0.5)
        k += 1

    # si se vencio el tiempo, retornar error
    if k == 30:
        return "No Se Pudo Continuar de Pop-Up de Inicio"

    # hacer click en boton
    popup_btn[0].click()

    # ingresar documento
    webdriver.find_element(By.ID, "mat-input-0").send_keys(doc_num)
    time.sleep(1)

    # click on "Si, acepto"
    checkbox = webdriver.find_element(By.ID, "mat-checkbox-2-input")
    webdriver.execute_script("arguments[0].click();", checkbox)
    time.sleep(1)

    # evadir captcha ("No Soy Un Robot")
    exito = evade_captcha(webdriver)
    if not exito:
        return "@Sin Solucion de Captcha"

    # click en Buscar
    webdriver.find_element(
        By.XPATH,
        "/html/body/app-root/div[2]/app-home/div/mat-card[1]/form/div[5]/div[1]/button",
    ).click()
    time.sleep(3)

    # si no hay informacion de usuario retornar blanco
    _test = webdriver.find_elements(By.ID, "swal2-html-container")
    if _test and "persona" in _test[0].text:
        # presionar "OK"
        try:
            btn = webdriver.find_element(
                By.XPATH, "/html/body/div[2]/div/div[6]/button[1]"
            )
            webdriver.execute_script("arguments[0].click();", btn)
        except Exception:
            webdriver.refresh()
        return []

    # alternativa sin datos: abre ventana pero no tiene pestañas, retornar en blanco
    x = webdriver.find_elements(
        By.XPATH,
        "/html/body/app-root/div[2]/app-search/div[2]/mat-tab-group/div/mat-tab-body[1]/div/div/div/mat-card/mat-card-content/div",
    )
    if x and "No cuenta con" in x[0].text:
        return []

    # scrape data
    _id_tipo = 11 if webdriver.find_elements(By.ID, "mat-input-11") else 17
    response = []
    for pos in (5, 6, _id_tipo, 7, 8, 9, 10):
        response.append(
            webdriver.find_element(
                By.ID,
                f"mat-input-{pos}",
            ).get_attribute("value")
        )

    # next tab (Puntos) - make sure all is populated before tabbing along (with timeout) and wait a little
    timeout = 0
    while not webdriver.find_elements(By.ID, "mat-tab-label-0-0"):
        time.sleep(1)
        timeout += 1
        if timeout > 10:
            webdriver.refresh()
            return "@Error en Puntos"
    time.sleep(1.5)

    action = ActionChains(webdriver)
    # enter key combination to open tabs
    for key in (Keys.TAB * 5, Keys.RIGHT, Keys.ENTER):
        action.send_keys(key)
        action.perform()
        time.sleep(0.5)

    # extract data
    _puntos = webdriver.find_element(
        By.XPATH,
        "/html/body/app-root/div[2]/app-search/div[2]/mat-tab-group/div/mat-tab-body[2]/div/div/mat-card/mat-card-content/div/app-visor-sclp/mat-card/mat-card-content/div/div[2]/label",
    )

    _puntos = int(_puntos.text.split(" ")[0]) if " " in _puntos.text else 0
    response.append(_puntos)

    # next tab (Record)
    time.sleep(0.8)
    action.send_keys(Keys.RIGHT)
    action.perform()
    time.sleep(0.7)
    action.send_keys(Keys.ENTER)
    action.perform()
    time.sleep(0.5)

    _recordnum = webdriver.find_element(
        By.XPATH,
        "/html/body/app-root/div[2]/app-search/div[2]/mat-tab-group/div/mat-tab-body[3]/div/div/mat-card/mat-card-content/div/app-visor-record/div[1]/div/mat-card-title",
    ).text
    response.append(_recordnum[9:] if _recordnum else None)

    # process completed succesfully
    webdriver.back()
    return response


def evade_captcha(webdriver):

    visible_checkbox = webdriver.find_element(
        By.CSS_SELECTOR, "mat-checkbox .mat-checkbox-inner-container"
    )

    # mueve el mouse y haz click, espera un segundo para que aparezca
    actions = ActionChains(webdriver)
    actions.move_to_element(visible_checkbox).click().perform()
    time.sleep(1)

    # extrae el texto de la imagen que se dene elegir
    try:
        descripcion_imagen = WebDriverWait(webdriver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//app-captcha-imagenes-popup//p")
            )
        )
    except TimeoutError:
        return False

    # del texto, la ultima palabra es la que dice que imagen elegir
    descripcion_imagen_texto = descripcion_imagen.text.split()[-1]

    if MTC_CAPTCHAS.get(descripcion_imagen_texto):
        for i in range(1, 9):
            _img_filename = f"https://licencias.mtc.gob.pe/assets/captcha/{MTC_CAPTCHAS[descripcion_imagen_texto]}.png"
            _element_xpath = f"/html/body/div/div[2]/div/mat-dialog-container/app-captcha-imagenes-popup/div/mat-dialog-content/app-captcha-imagenes/div[2]/div[{i}]/img"
            element = webdriver.find_element(By.XPATH, _element_xpath)
            if element.get_attribute("src") == _img_filename:
                element.click()
                time.sleep(1)
                return True

    return False
