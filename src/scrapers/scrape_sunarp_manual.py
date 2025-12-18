from selenium.webdriver.common.by import By
import time


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

    # x = webdriver.find_elements(By.XPATH, "/html/body//div/div/div[1]/div/label/input")
    # if x:
    #     webdriver.execute_script("arguments[0].click();", x[0])
    #     time.sleep(2)

    # ingresar datos de placa y esperar a captcha ok
    webdriver.find_element(By.ID, "nroPlaca").send_keys(placa)
    time.sleep(15)

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
