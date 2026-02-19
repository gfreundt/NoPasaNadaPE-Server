from datetime import datetime as dt
import os
import re
import sys
import json
from tqdm import tqdm
import requests

# local imports
from security.keys import OCRSPACE_API_KEY
from src.utils.utils import NETWORK_PATH
from client_api import get_sunarp, manual_upload
from seleniumbase import SB


def gather(data):

    response = []

    for placa in data:
        # send request to scraper
        scraper_response = scrape(placa=placa)

        # respuesta es en blanco
        if not scraper_response:
            response.append(
                {
                    "Empty": True,
                    "PlacaValidate": placa,
                }
            )
            continue

        _now = dt.now().strftime("%Y-%m-%d")

        ocr = ocrspace_pdf_bytes(pdf_bytes=scraper_response, language="esp")

        # add foreign key and current date to response
        response.append(
            {
                "IdPlaca_FK": 999,
                "PlacaValidate": placa,
                "Serie": ocr.get("serie"),
                "VIN": ocr.get("vin"),
                "Motor": ocr.get("motor"),
                "Color": ocr.get("color"),
                "Marca": ocr.get("marca"),
                "Modelo": ocr.get("modelo"),
                "Ano": ocr.get("ano"),
                "PlacaVigente": ocr.get("placa_vigente"),
                "PlacaAnterior": ocr.get("placa_anterior"),
                "Estado": ocr.get("estado"),
                "Anotaciones": ocr.get("anotaciones"),
                "Sede": ocr.get("sede"),
                "Propietarios": ocr.get("propietarios"),
                "ImageBytes": scraper_response,
                "LastUpdate": _now,
            }
        )

    with open(
        os.path.join(NETWORK_PATH, "security", "update_manual_sunarp.json"),
        mode="w",
    ) as outfile:
        outfile.write(json.dumps({"DataSunarpFichas": response}))


def scrape(placa):
    url = "https://consultavehicular.sunarp.gob.pe/consulta-vehicular"

    # Initialize the progress bar with the total number of steps (6)
    pbar = tqdm(total=6, desc=f"Scraping {placa}", unit="step")

    try:
        with SB(uc=True, headless=False) as sb:
            # Step 1: Activate CDP
            sb.activate_cdp_mode()
            sb.set_window_size(1920, 1080)
            pbar.update(1)

            # Step 2: Open URL
            sb.open(url)
            sb.sleep(6)
            pbar.update(1)

            # Step 3: Click Captcha
            sb.uc_gui_click_captcha()
            sb.sleep(2)
            pbar.update(1)

            # Step 4: Type Placa
            sb.type("#nroPlaca", placa)
            sb.sleep(1)
            pbar.update(1)

            # Step 5: Click Submit
            sb.click("button")
            sb.sleep(5)
            pbar.update(1)

            # Step 6: Finalize/Image Extraction
            result = get_vehicle_image_base64(sb)
            pbar.update(1)

            pbar.close()  # Close bar on success
            return result

    except Exception as e:
        pbar.set_description(f"Error on {placa}")
        pbar.close()  # Close bar on failure
        return []


def get_vehicle_image_base64(sb):

    # Wait until the image exists in the DOM
    sb.wait_for_element_present(".container-data-vehiculo img", timeout=15)

    # Get the data URL
    data_url = sb.get_attribute(".container-data-vehiculo img", "src")

    if not data_url.startswith("data:image"):
        raise RuntimeError("Image src is not a data URL")

    # Return ONLY the Base64 payload (JSON-safe)
    return data_url.split(",", 1)[1]


def ocrspace_pdf_bytes(pdf_bytes, language):

    url = "https://api.ocr.space/parse/image"

    # OCR.space expects a multipart upload. Field name should be "file".
    files = {"file": ("image.png", pdf_bytes, "image/png")}

    data = {
        "apikey": OCRSPACE_API_KEY,
        "language": language,
        "isOverlayRequired": False,
        "scale": True,  # helps when text is small
        "OCREngine": 2,  # engine 2 is usually better
        "detectOrientation": True,  # rotate if needed
        "isTable": False,  # set True only if you want table-style parsing
    }

    r = requests.post(url, files=files, data=data, timeout=120)
    r.raise_for_status()
    payload = r.json()

    # Basic error handling
    if payload.get("IsErroredOnProcessing"):
        msg = (
            payload.get("ErrorMessage")
            or payload.get("ErrorDetails")
            or "Unknown OCR error"
        )
        raise RuntimeError(f"OCR.space error: {msg}")

    parsed_results = payload.get("ParsedResults") or []
    if not parsed_results:
        return ""

    # OCR.space returns one ParsedResults entry per page (for PDFs).
    text_pages = []
    for page in parsed_results:
        text_pages.append(page.get("ParsedText", ""))

    text = "".join(i.strip().upper() for i in text_pages if i is not None)
    final_text = []

    for t in text.splitlines():
        r = [i.strip() for i in t.split(":") if len(i) > 1]
        final_text += r

    return extract_values_from_text(final_text)


def extract_values_from_text(text):

    resultado = {}

    VIN_PATRON = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
    INDICE = [
        ("MOTOR", ""),
        ("VIGENTE", ""),
        ("ANTERIOR", ""),
        ("MARCA", ""),
        ("MODELO", "AÑO"),
        ("COLOR", ""),
        ("ESTADO", ""),
        ("ANOTACIONES", ""),
        ("SEDE", ""),
        ("AÑO", ""),
    ]
    for pos, contenido in enumerate(text + [""]):
        # vin
        if VIN_PATRON.match(contenido.upper()):
            resultado["vin"] = contenido.upper()

        # propietarios
        if "PROPIETARIO" in contenido:
            propietarios = []
            for i in text[pos + 1 :]:
                if "/" in i:
                    break
                else:
                    propietarios.append(i)
            resultado["propietarios"] = " Y ".join(propietarios)

        # los demas
        for hay, no_hay in INDICE:
            if not no_hay:
                no_hay = "***"
            if hay in contenido and no_hay not in contenido:
                if text[pos + 1]:
                    resultado[hay.lower()] = text[pos + 1].upper()
                    break
                else:
                    resultado[hay.lower()] = ""

    # post-procesamiento especifico

    # año sacado de VIN si no sale directo de imagen
    ano_vin = ano_segun_vin(resultado.get("vin"))
    if not resultado["año"].isdigit():
        resultado["año"] = ano_vin if ano_vin else ""

    # eliminar "RP" en anotaciones
    resultado["anotaciones"] = resultado["anotaciones"].replace("RPNINGUNA", "NINGUNA")

    # si se encuentra la palabra "LIMA" reemplazarla manualmente para sede
    if "LIMA" in text:
        resultado["sede"] = "LIMA"

    return resultado


def ano_segun_vin(vin):

    try:
        if vin is None or len(vin) != 17:
            return False

        clave = {
            "A": [1980, 2000, 2020],
            "B": [1981, 2011, 2021],
            "C": [1982, 2012, 2022],
            "D": [1983, 2013, 2023],
            "E": [1984, 2014, 2024],
            "F": [1985, 2015, 2025],
            "G": [1986, 2016, 2026],
            "H": [1987, 2017, 2027],
            "J": [1988, 2018, 2028],
            "K": [1989, 2019, 2029],
            "L": [1990, 2010],
            "M": [1991, 2011],
            "N": [1992, 2012],
            "P": [1993, 2013],
            "R": [1994, 2014],
            "S": [1995, 2015],
            "T": [1996, 2016],
            "V": [1997, 2017],
            "W": [1998, 2018],
            "X": [1999, 2019],
            "1": [2001],
            "2": [2002],
            "3": [2003],
            "4": [2004],
            "5": [2005],
            "6": [2006],
            "7": [2007],
            "8": [2008],
            "9": [2009],
        }

        return clave[vin[9]][0]

    except Exception:
        return False


def update(url):
    manual_upload(url=url, filename="update_manual_sunarp.json")


def main():

    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    else:
        n = 3  # default number of placas to process

    url = "https://nopasanadape.com"  # PROD

    # get placas that need updating
    data = get_sunarp(url).json().get("DataSunarpFichas")
    print(f"Before ({len(data)}):", data)

    # get the data from n placas
    gather(data[:n])

    # update database
    update(url)

    # get placas that need updating (used to compare to original)
    data = get_sunarp(url).json().get("DataSunarpFichas")
    print(f"After ({len(data)}):", data)


if __name__ == "__main__":
    main()
