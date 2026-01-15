from datetime import datetime as dt, timedelta as td
import os
import json

# local imports
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

        # add foreign key and current date to response
        response.append(
            {
                "IdPlaca_FK": 999,
                "PlacaValidate": placa,
                "Serie": "",
                "VIN": "",
                "Motor": "",
                "Color": "",
                "Marca": "",
                "Modelo": "",
                "Ano": "",
                "PlacaVigente": "",
                "PlacaAnterior": "",
                "Estado": "",
                "Anotaciones": "",
                "Sede": "",
                "Propietarios": "",
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

    try:
        with SB(uc=True, headless=False) as sb:
            print("**1")
            sb.activate_cdp_mode()
            sb.set_window_size(1920, 1080)
            print("**2")
            sb.open(url)
            sb.sleep(8)
            print("**3")
            sb.uc_gui_click_captcha()
            sb.sleep(2)
            print("**4")
            sb.type("#nroPlaca", placa)
            sb.sleep(1)
            print("**5")
            sb.click("button")
            sb.sleep(5)
            print("**6")
            return get_vehicle_image_base64(sb)
    except Exception:
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


def main():

    url = "http://localhost:5000"  # TEST
    url = "https://nopasanadape.com"  # PROD

    data = get_sunarp(url).json().get("DataSunarpFichas")
    print(f"Before ({len(data)}):", data)
    gather(data[:10])
    update(url)
    data = get_sunarp(url).json().get("DataSunarpFichas")
    print(f"After ({len(data)}):", data)


if __name__ == "__main__":
    main()
