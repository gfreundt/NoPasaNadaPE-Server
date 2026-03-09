import os
import io
import base64
import time
import uuid
import shutil
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from src.utils.utils import use_truecaptcha


def browser(datos, webdriver):

    doc_num = datos["DocNum"]

    url = "https://recordconductor.mtc.gob.pe/"

    intentos_captcha = 0
    while intentos_captcha < 5:
        if webdriver.current_url != url:
            webdriver.get(url)
            time.sleep(2)

        try:
            # extraer texto de captcha
            _captcha_file_like = io.BytesIO(
                webdriver.find_element(By.ID, "idxcaptcha").screenshot_as_png
            )
            captcha_txt = use_truecaptcha(_captcha_file_like)["result"]
            if not captcha_txt:
                return "Servicio Captcha Offline."

            # ingresar en formulario y apretar buscar
            try:
                t = WebDriverWait(webdriver, 7).until(
                    EC.visibility_of_element_located((By.ID, "txtNroDocumento"))
                )
                t.send_keys(doc_num)
            except TimeoutException:
                return "Campo no puede interactuar"

            webdriver.find_element(By.ID, "idCaptcha").send_keys(captcha_txt)
            time.sleep(1)

            # esperar a que boton se pueda presionar
            try:
                b = WebDriverWait(webdriver, 7).until(
                    EC.element_to_be_clickable((By.ID, "BtnBuscar"))
                )
                b.click()
            except TimeoutException:
                return "Boton no se puede presionar"

            time.sleep(3)

            # obtener mensaje de alerta (si hay)
            _alerta = webdriver.find_elements(
                By.XPATH, "/html/body/div[5]/div/div/div[1]/label"
            )

            # mensaje de alerta: captcha equivocado
            if _alerta and "ingresado" in _alerta[0].text:
                # refrescar captcha (presionar boton) para siguiente iteracion
                webdriver.refresh()
                intentos_captcha += 1
                time.sleep(3)
                continue

            # mensaje de alerta: no hay informacion de la persona
            elif _alerta and "PERSONA" in _alerta[0].text:
                return []

        except ValueError:
            # no carga imagen de captcha, refrescar pagina y volver a intentar
            webdriver.refresh()
            intentos_captcha += 1
            time.sleep(3)
            return "No Carga Captcha"

        # -- inicia extraccion de datos

        # crear un directorio al azar dentro de /tmp para evitar conflictos entre
        # workers bajando diferentes archivos con el mismo nombre a la vez
        download_dir = os.path.join("/tmp", f"mtc_{uuid.uuid4().hex}")
        os.makedirs(download_dir, exist_ok=True)

        # parametros necesarios para que no abra ventana de dialogo de "Guardar Como..." y folder destino
        webdriver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": download_dir,
            },
        )

        # apretar boton que lleva a bajar archivo
        b = webdriver.find_elements(By.ID, "btnprint")
        try:
            webdriver.execute_script("arguments[0].click();", b[0])
            time.sleep(2)

        except Exception:
            webdriver.refresh()
            return "@No Hay Boton Download"

        # esperar un tiempo hasta que baje el archivo
        archivo_descargado = os.path.join(download_dir, "RECORD DE CONDUCTOR.pdf")

        start_time = time.time()
        while time.time() - start_time < 12:
            if os.path.isfile(archivo_descargado):
                # cargar imagen en bytes en memoria
                with open(archivo_descargado, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")

                # borrar folder (y contenido) y devolver la imagen en bytes
                shutil.rmtree(download_dir, ignore_errors=True)
                return [[data]]

            time.sleep(1)

        # si no se encontro imagen, retornar error
        return "No Se Puedo Bajar Archivo"

    # demasiados intentos de captcha errados consecutivos
    return "Excede Intentos de Captcha"
