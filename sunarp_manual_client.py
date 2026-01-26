from datetime import datetime as dt
import os
import sys
import json
from tqdm import tqdm
import requests
import base64

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


def update(url):
    manual_upload(url=url, filename="update_manual_sunarp.json")


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


def get_vehicle_image_base64(sb) -> str:

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

    # serie, vib, motor, color, marca, modelo, ano, placavigente, placanterior, estado, anotaciones, sede, propietarios
    resultado = {}
    for pos, contenido in enumerate(text + [""]):

        if "SERIE" in contenido:
            resultado.update({"serie": text[pos + 1]})
        if "VIN" in contenido:
            resultado.update({"vin": text[pos + 1]})
        if "MOTOR" in contenido:
            resultado.update({"motor": text[pos + 1]})
        if "COLOR" in contenido:
            resultado.update({"color": text[pos + 1]})
        if "MARCA" in contenido:
            resultado.update({"marca": text[pos + 1]})
        if "MODELO" in contenido and "AÑO" not in contenido:
            resultado.update({"modelo": text[pos + 1]})
        if "VIGENTE" in contenido:
            resultado.update({"placa_vigente": text[pos + 1]})
        if "ANTERIOR" in contenido:
            resultado.update({"placa_anterior": text[pos + 1]})
        if "ESTADO" in contenido:
            resultado.update({"estado": text[pos + 1]})
        if "ANOTACIONES" in contenido:
            t = text[pos + 1]
            t = "NINGUNA" if t == "RPNINGUNA" else t
            resultado.update({"anotaciones": t})
        if "SEDE" in contenido:
            resultado.update({"sede": text[pos + 1]})
        if "AÑO" in contenido:
            resultado.update({"ano": text[pos + 1]})
        if "PROPIETARIOS" in contenido:
            resultado.update({"propietarios": text[pos + 1]})

    return resultado


def main():

    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    else:
        n = 3  # default number of placas to process

    url = "https://nopasanadape.com"  # PROD

    data = get_sunarp(url).json().get("DataSunarpFichas")
    print(f"Before ({len(data)}):", data)
    gather(data[:n])
    update(url)
    data = get_sunarp(url).json().get("DataSunarpFichas")
    print(f"After ({len(data)}):", data)


if __name__ == "__main__":
    main()
