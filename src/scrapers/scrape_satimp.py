import time
import io
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

# local imports
from func_timeout import func_set_timeout, exceptions
from src.utils.utils import use_truecaptcha
from src.utils.constants import SCRAPER_TIMEOUT


@func_set_timeout(SCRAPER_TIMEOUT["satimps"])
def browser_wrapper(doc_num, doc_tipo, webdriver):
    try:
        return browser(doc_num, doc_tipo, webdriver)
    except exceptions.FunctionTimedOut:
        return "Timeout"


def browser(doc_num, doc_tipo, webdriver):

    url_inicial = "https://www.sat.gob.pe/WebSitev8/IncioOV2.aspx"
    webdriver.get(url_inicial)

    # extraer codigo de sesion y navegar a url final
    url_final = (
        "https://www.sat.gob.pe/VirtualSAT/modulos/TributosResumen.aspx?tri=T&mysession="
        + webdriver.current_url.split("=")[-1]
    )

    intentos_captcha = 0
    while intentos_captcha < 5:

        # abrir url
        if webdriver.current_url != url_final:
            webdriver.get(url_final)
            time.sleep(2)

        # extraer texto de captcha
        _captcha_img = webdriver.find_element(
            By.XPATH,
            "/html/body/form/div[3]/section/div/div/div[2]/div[3]/div[5]/div/div[1]/div[2]/div/img",
        )
        _img = io.BytesIO(_captcha_img.screenshot_as_png)
        captcha_txt = use_truecaptcha(_img)["result"]
        if not captcha_txt:
            return "Servicio Captcha Offline."

        # select alternative option from dropdown to reset it
        drop = Select(webdriver.find_element(By.ID, "tipoBusqueda"))
        drop.select_by_value("busqCodAdministrado")
        time.sleep(0.5)

        # select Busqueda por Documento from dropdown
        drop.select_by_value("busqTipoDocIdentidad")
        time.sleep(0.5)

        # select tipo documento (DNI/CE) from dropdown
        drop = Select(webdriver.find_element(By.ID, "ctl00_cplPrincipal_ddlTipoDocu"))
        drop.select_by_value("4" if doc_tipo == "CE" else "2")
        time.sleep(0.5)

        # clear field and enter DNI/CE
        _dnice = webdriver.find_element(By.ID, "ctl00_cplPrincipal_txtDocumento")
        _dnice.clear()
        _dnice.send_keys(doc_num)

        # clear field and enter captcha
        _captcha_field = webdriver.find_element(By.ID, "ctl00_cplPrincipal_txtCaptcha")
        _captcha_field.clear()
        _captcha_field.send_keys(captcha_txt)
        time.sleep(0.5)

        # click BUSCAR
        webdriver.find_element(By.CLASS_NAME, "boton").click()
        time.sleep(0.5)

        # determina si hay datos disponibles
        _msg = webdriver.find_element(
            By.ID, "ctl00_cplPrincipal_lblMensajeCantidad"
        ).text
        if not _msg:
            # captcha equivocado, reintentar
            intentos_captcha += 1
            continue

        # empieza extraccion
        _qty = int("".join([i for i in _msg if i.isdigit()]))

        # no hay registro, regresar blanco
        if _qty == 0:
            return []

        # entra a cada codigo y para cada uno extrae informacion de deudas asociadas
        response = []
        for row in range(_qty):
            codigo = webdriver.find_element(
                By.ID, f"ctl00_cplPrincipal_grdAdministrados_ctl0{row+2}_lnkCodigo"
            ).text

            webdriver.find_element(
                By.ID, f"ctl00_cplPrincipal_grdAdministrados_ctl0{row+2}_lnkNombre"
            ).click()
            time.sleep(0.5)

            _deudas = []
            webdriver.find_element(By.ID, "ctl00_cplPrincipal_rbtMostrar_2").click()
            time.sleep(0.5)

            for i in range(2, 10):
                _placeholder = f"ctl00_cplPrincipal_grdEstadoCuenta_ctl0{i}_lbl"
                y = f"{_placeholder}Anio"
                x = webdriver.find_elements(By.ID, y)
                if x:
                    periodo = webdriver.find_element(
                        By.ID, f"{_placeholder}Periodo"
                    ).text

                    # reducir a 4 cualquier numero mayor
                    periodo = min(int(periodo), 4)
                    ano = x[0].text

                    # fecha es la ultima del trimestre para fines de alertas
                    _f = ("03-31", "06-30", "09-30", "12-31")
                    fecha_hasta = f"{ano}-{_f[periodo-1]}"
                    _fila = [
                        ano,
                        periodo,
                        webdriver.find_element(By.ID, f"{_placeholder}Documento").text,
                        webdriver.find_element(By.ID, f"{_placeholder}Deuda").text,
                        fecha_hasta,
                    ]
                    _deudas.append(_fila)

            # retroceder a pagina de codigos (dos saltos)
            webdriver.back()
            time.sleep(1)
            webdriver.back()
            time.sleep(1)

            # armar respuesta con datos de este codigo, pasar al siguiente
            response.append({"codigo": int(codigo), "deudas": _deudas})

        # presionar "nueva busqueda" para dejar listo para la siguiente iteracion y regresar respuesta
        time.sleep(0.5)
        webdriver.find_element(By.ID, "ctl00_cplPrincipal_btnNuevaBusqueda").click()
        return response

    # demasiados intentos de captcha errados consecutivos
    return "Excede Intentos de Captcha"
