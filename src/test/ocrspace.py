import requests
import re
import base64
from security.keys import OCRSPACE_API_KEY
from pprint import pprint


def main(db):

    cursor = db.cursor()
    cursor.execute(
        "SELECT PlacaValidate, ImageBytes FROM DataSunarpFichas WHERE ImageBytes IS NOT NULL"
    )
    for i in cursor.fetchall():
        ocr_response = ocrspace_pdf_bytes(
            pdf_bytes=base64.b64decode(i["ImageBytes"]), language="spa"
        )
        x = extract_values_from_text(ocr_response)
        pprint(x)

        cmd = """ UPDATE DataSunarpFichas 
                    SET VIN = ?,
                        Motor = ?,
                        Color = ?,
                        Marca = ?,
                        Modelo = ?,
                        Ano = ?,
                        PlacaVigente = ?,
                        PlacaAnterior = ?,
                        Estado = ?,
                        Anotaciones = ?,
                        Sede = ?,
                        Propietarios = ?
                    WHERE
                        PlacaValidate = ?

                
                    
            """
        val = (
            x.get("vin"),
            x.get("motor"),
            x.get("color"),
            x.get("marca"),
            x.get("modelo"),
            x.get("año"),
            x.get("vigente"),
            x.get("anterior"),
            x.get("estado"),
            x.get("anotaciones"),
            x.get("sede"),
            x.get("propietarios"),
            i["PlacaValidate"],
        )

        cursor.execute(cmd, val)

    conn = db.conn
    conn.commit()


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

    return final_text


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
