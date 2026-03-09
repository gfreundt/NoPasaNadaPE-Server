import time
import io
import os
import base64
import json
from datetime import datetime as dt
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from PIL import Image, ImageDraw, ImageFont

from src.utils.constants import NETWORK_PATH
from src.utils.utils import use_truecaptcha, img_to_pdf


def browser(datos, webdriver):

    placa = datos["Placa"]

    intentos_captcha = 0
    while intentos_captcha < 5:
        # abrir url
        webdriver.set_page_load_timeout(45)  # seconds
        url = "https://www.apeseg.org.pe/consultas-soat/"

        try:
            webdriver.get(url)
            time.sleep(2)
        except TimeoutException:
            webdriver.execute_script("window.stop();")
            time.sleep(2)
            _btn = webdriver.find_elements(
                By.ID, "/html/body/div/div/main/div/form/button"
            )
            if not _btn:
                webdriver.refresh()
                time.sleep(2)
                continue

        # cambiar a frame
        webdriver.switch_to.frame(0)
        time.sleep(2)

        # extraer imagen de captcha y enviar a procesar
        _img = webdriver.find_element(By.CLASS_NAME, "captcha-img")
        captcha_file_like = io.BytesIO(_img.screenshot_as_png)
        captcha_txt = use_truecaptcha(captcha_file_like).get("result")
        if not captcha_txt:
            return "Servicio Captcha Offline."

        # ingresar placa en campo
        webdriver.find_element(By.ID, "placa").send_keys(placa)

        # ingresar captcha en campo
        webdriver.find_element(By.ID, "captcha").send_keys(captcha_txt)
        # apretar "Consultar"
        but = webdriver.find_element(
            By.XPATH, "/html/body/div/div/main/div/form/button"
        )
        webdriver.execute_script("arguments[0].click();", but)
        time.sleep(3)
        # detectar captcha incorrecto, intentar otra vez
        msg = webdriver.find_elements(By.XPATH, "/html/body/div/div/main/div/form/p")
        if msg and "incorrecto" in msg[0].text:
            intentos_captcha += 1
            webdriver.refresh()
            time.sleep(2)
            continue
        # sin respuesta
        msg = webdriver.find_elements(By.XPATH, "/html/body/div/div/main/div/div/h2")
        if msg and "la placa solicitada" in msg[0].text:
            webdriver.quit()
            return []
        # extraer data de respuesta (espera hasta 10 segundos que aparezca)

        # busca datos, si no existen responder con error de scraper
        try:
            WebDriverWait(webdriver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "/html/body/div/div/main/div/div/table/tbody/tr[1]/td")
                )
            )
            response = [
                webdriver.find_element(
                    By.XPATH,
                    f"/html/body/div/div/main/div/div/table/tbody/tr[{i}]/td",
                ).text.strip()
                for i in range(1, 13)
            ]
            # agrega a las respuestas del scraper una imagen creada con los datos
            response.append(generar_certificado(response))

        except (
            TimeoutException,
            StaleElementReferenceException,
            NoSuchElementException,
        ):
            response = "@Sin Datos"

        return [response]

    # error en respuesta
    return "Exceso Reintentos Captcha"


def generar_certificado(data):

    with open(
        os.path.join(NETWORK_PATH, "static", "soat", "datos_aseguradoras.json"), "r"
    ) as file:
        datos_aseguradora = json.load(file).get(data[0])

    # load fonts
    fonts = os.path.join(NETWORK_PATH, "static", "fonts")
    font_chico = ImageFont.truetype(os.path.join(fonts, "seguisym.ttf"), 30)
    font_grande = ImageFont.truetype(os.path.join(fonts, "seguisym.ttf"), 45)

    # open blank template image and prepare for edit
    _templates_path = os.path.join(NETWORK_PATH, "static", "soat", "imagenes")
    base_img = Image.open(os.path.join(_templates_path, "certificado_en_blanco.png"))
    editable_img = ImageDraw.Draw(base_img)

    # if logo in database add it to image, else add word
    try:
        logo = Image.open(os.path.join(_templates_path, f"{data[0]}.png"))
        logo_width, logo_height = logo.size
        logo_pos = (10 + (340 - logo_width) // 2, 250 + (120 - logo_height) // 2)

        # add insurance company logo to image
        base_img.paste(logo, logo_pos)

        # add insurance company phone number to image
        telefono = datos_aseguradora.get("telefono")
        editable_img.text(
            (400, 275),
            telefono or "",
            font=font_grande,
            fill=(59, 22, 128),
        )
    except Exception:
        editable_img.text(
            (40, 275), data[0].upper(), font=font_grande, fill=(59, 22, 128)
        )

    # positions for each text in image
    coordinates = [
        (40, 516, 7),  # Certificado
        (40, 588, 2),  # Desde (izq)
        (40, 665, 3),  # Hasta (izq)
        (337, 588, 2),  # Desde (der)
        (337, 665, 3),  # Hasta (der)
        (40, 819, 4),  # Placa
        (40, 897, 9),  # Categoria
        (40, 970, 6),  # Uso
        (406, 971, 3),  # Fecha
    ]

    # loop through all positions and add them to image
    for c in coordinates:
        editable_img.text(
            (c[0], c[1]), data[c[2]].upper(), font=font_chico, fill=(59, 22, 128)
        )

    img_byte_arr = io.BytesIO()
    base_img.save(img_byte_arr, format="PNG")

    pdf_bytes = img_to_pdf(img_byte_arr.getvalue())
    return base64.b64encode(pdf_bytes).decode("utf-8")
