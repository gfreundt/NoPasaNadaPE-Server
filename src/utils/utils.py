from datetime import datetime as dt
import re
import base64
import socket
import bcrypt
import json
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException
from src.utils.constants import MONTHS_3_LETTERS
from security.keys import PUSHBULLET_API_TOKEN


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


def base64_to_image(base64_string, output_path):
    try:
        image_data = base64.b64decode(base64_string)
        with open(output_path, "wb") as file:
            file.write(image_data)
    except Exception as e:
        print(f"An error occurred (base64_to_image): {e}")


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 1))  # connect() for UDP doesn't send packets
    return s.getsockname()[0]


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
