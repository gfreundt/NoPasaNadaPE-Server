from datetime import datetime as dt
import io
import re
import os
import base64
import socket
import bcrypt
import json
import requests
import subprocess
import time
from requests.exceptions import Timeout, ConnectionError, RequestException
from PIL import Image, ImageDraw, ImageFont
from selenium.webdriver.common.by import By
import fcntl


from src.utils.constants import MONTHS_3_LETTERS, NETWORK_PATH
from security.keys import PUSHBULLET_API_TOKEN, TRUECAPTCHA_API_KEY, TWOCAPTCHA_API_KEY

# --- GUNICORN ---


def is_master_worker(db):
    lock_path = "/tmp/dashboard_init.lock"
    db._lock_file_handle = open(lock_path, "a")

    try:
        fcntl.flock(db._lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (OSError, BlockingIOError):
        db._lock_file_handle.close()
        db._lock_file_handle = None
        return False


# ----- FORMATTING ----


def date_to_db_format(data):
    """Takes dd.mm.yyyy date formats with different separators and returns yyyy-mm-dd."""

    # define valid patterns, everything else is returned as is
    pattern = r"^(0[1-9]|[12][0-9]|3[01])[/-](0[1-9]|1[012])[/-]\d{4}$"

    new_record_dates_fixed = []

    for data_item in data:

        # test to determine if format is date we can change to db format
        try:
            if re.fullmatch(pattern, data_item):
                # if record has date structure, alter it, everything else throws exception and no changes made
                sep = "/" if "/" in data_item else "-" if "-" in data_item else None
                new_record_dates_fixed.append(
                    dt.strftime(dt.strptime(data_item, f"%d{sep}%m{sep}%Y"), "%Y-%m-%d")
                )

            else:
                new_record_dates_fixed.append(data_item)

        except Exception:
            new_record_dates_fixed.append(data_item)

    return new_record_dates_fixed


def date_to_mail_format(fecha, delta=False, elapsed=False):
    _day = fecha[8:]
    _month = MONTHS_3_LETTERS[int(fecha[5:7]) - 1]
    _year = fecha[:4]

    _extratxt = ""
    _delta = int((dt.strptime(fecha, "%Y-%m-%d") - dt.now()).days)
    if delta:
        _extratxt = f"[ en {_delta:,} días ]" if _delta > 0 else "[ VENCIDO ]"
    if elapsed:
        _extratxt = f"[ hace {-_delta:,} días ]" if -_delta > 1 else "[ HOY ]"

    return f"{_day}-{_month}-{_year} {_extratxt}"


def date_to_user_format(fecha):
    # change date format to a more legible one

    _months = (
        "Ene",
        "Feb",
        "Mar",
        "Abr",
        "May",
        "Jun",
        "Jul",
        "Ago",
        "Sep",
        "Oct",
        "Nov",
        "Dic",
    )
    _day = fecha[8:]
    _month = _months[int(fecha[5:7]) - 1]
    _year = fecha[:4]

    return f"{_day}-{_month}-{_year}"


# ----- NETWORKING ----


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 1))  # connect() for UDP doesn't send packets
    return s.getsockname()[0]


def start_vpn(pais="pe", con_tipo="udp"):
    """
    Starts the OpenVPN connection in daemon mode.
    Requires sudo privileges.
    Returns process successful (True/False)
    """

    vpn_location = "pe-lim" if pais.lower() == "pe" else "ar-bua"

    try:
        subprocess.run(
            [
                "sudo",
                "openvpn",
                "--config",
                rf"/etc/openvpn/client/{vpn_location}.prod.surfshark.com_{con_tipo.lower()}.ovpn",
                "--daemon",
            ],
            text=True,
            check=True,
        )

    except subprocess.CalledProcessError:
        return False

    time.sleep(2)
    return vpn_online()


def stop_vpn():
    """
    Stops all running OpenVPN processes.
    Requires sudo privileges.
    """
    subprocess.run(["sudo", "pkill", "openvpn"], check=False)
    time.sleep(0.5)


def switch_vpn(current):
    """
    Stops all running OpenVPN processes.
    Requires sudo privileges.
    """
    stop_vpn()
    return start_vpn(pais="ar" if current == "pe" else "pe")


def get_public_ip():
    """
    Prints the current public IPv4 address.
    """
    result = subprocess.run(
        ["curl", "-4", "-s", "ifconfig.me"], capture_output=True, text=True, check=True
    )

    result.stdout.strip()


def vpn_online():
    """
    Returns True if an OpenVPN process is running, False otherwise.
    """
    result = subprocess.run(
        ["pgrep", "-x", "openvpn"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    return result.returncode == 0


# ---- DATA TRANSFORMATION -----


def base64_to_image(base64_string, output_path):
    try:
        image_data = base64.b64decode(base64_string)
        with open(output_path, "wb") as file:
            file.write(image_data)
    except Exception as e:
        print(f"An error occurred (base64_to_image): {e}")


def hash_text(text_string):

    # plain text to bytes
    text_bytes = text_string.encode("utf-8")

    # generate random salt
    _salt = bcrypt.gensalt(rounds=12)

    # hash bytes using salt and return as plain text
    hash_bytes = bcrypt.hashpw(text_bytes, _salt)
    return hash_bytes.decode("utf-8")


def compare_text_to_hash(text_string, hash_string):

    # convert strings to bytes
    text_bytes = text_string.encode("utf-8")
    hash_bytes = hash_string.strip().encode("utf-8")

    # return boolean on match
    return bcrypt.checkpw(text_bytes, hash_bytes)


# ----- MESSAGING -----


def send_pushbullet(title, message=""):

    # do not accept blank title
    if not title:
        return False

    API_URL = "https://api.pushbullet.com/v2/pushes"
    payload = {"type": "note", "title": title, "body": message}

    try:
        response = requests.post(
            API_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            auth=(PUSHBULLET_API_TOKEN, ""),
        )

        if response.status_code == 200:
            return True
        else:
            return False

    except (Timeout, ConnectionError, RequestException):
        return False


# --- CAPTCHA SOLVERS ---


def use_truecaptcha(image, retries=3):
    """
    Recibe imagen y la envia al servicio externo de deteccion TRUECAPTCHA
    para transformarlo en texto

    :param image: Objeto en Bytes
    :param retries: Cuantas veces volver a intentar si el servicio esta offline

    Correcto: retorna diccionario, con el texto en llave "result"
    Error: retorna False
    """

    # legacy: transform received path to object
    if type(image) is str:
        image = open(image, "rb")

    retry_attempts = 0
    _url = "https://api.apitruecaptcha.org/one/gettext"
    _data = {
        "userid": "gabfre@gmail.com",
        "apikey": TRUECAPTCHA_API_KEY,
        "data": base64.b64encode(image.read()).decode("ascii"),
    }
    while True:
        try:
            response = requests.post(url=_url, json=_data)
            return response.json()
        except ConnectionError:
            retry_attempts += 1
            if retry_attempts <= retries:
                time.sleep(10)
                continue
            return False


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
        for _ in range(48):  # ~8 minutes max
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


def create_soat_certificate(data):
    """Generates a SOAT certificate image (Mock implementation from gather_soats.py)."""
    _resources = os.path.join(r"D:\pythonCode", "Resources", "Fonts")
    font_small = ImageFont.truetype(os.path.join(_resources, "seguisym.ttf"), 30)
    font_large = ImageFont.truetype(os.path.join(_resources, "seguisym.ttf"), 45)

    # get list of available company logos (Mocking a list)
    _templates_path = os.path.join(NETWORK_PATH, "static")
    # cias = [i.split(".")[0] for i in os.listdir(_templates_path)]

    # open blank template image and prepare for edit (Mocking a simple image)
    base_img = Image.new("RGB", (800, 1200), color="white")
    editable_img = ImageDraw.Draw(base_img)

    # Mock adding text
    editable_img.text(
        (40, 50), f"SOAT Certificate: {data[4]}", font=font_large, fill=(0, 0, 0)
    )
    editable_img.text(
        (40, 100), f"Aseguradora: {data[0]}", font=font_small, fill=(0, 0, 0)
    )

    # Save image to memory buffer
    buffer = io.BytesIO()
    base_img.save(buffer, format="JPEG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")
