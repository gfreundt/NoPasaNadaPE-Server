import os
import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# paths
if platform.system() == "Linux":
    if platform.node() == "power":
        NETWORK_PATH = os.path.join("/mnt", "gce")
        NETWORK_PATH = os.path.join("/home", "gfreundt", "NoPasaNadaPE-Server")
    elif platform.node() == "nopasanada-server":
        NETWORK_PATH = os.path.join("/home", "nopasanadape", "NoPasaNadaPE-Server")
    else:
        if "/var/www/app" in BASE_DIR:
            NETWORK_PATH = "/var/www/nopasanadape/app"
        elif "/var/www/app-dev" in BASE_DIR:
            NETWORK_PATH = "/var/www/nopasanadape-dev/app"
        # NETWORK_PATH = os.path.join("/var", "www", "nopasanadape", "app")
elif platform.system() == "Windows":
    NETWORK_PATH = os.path.join(
        r"\\192.168.68.110",
        "d",
        "pythonCode",
        "nopasanada",
    )
else:
    NETWORK_PATH = os.path.join("/var", "www", "app")

DB_NETWORK_PATH = os.path.join(NETWORK_PATH, "data", "members.db")

# =========== TOKENS DE SEGURIDAD LOCALES ============

# token usado por usuarios internos para actualizar BD
UPDATER_TOKEN = """b3BlbnNzaC1rZXktdjEAAAAACmFlczI1Ni1jdHIAAAAGYmNyeXB0AAAAGAAAABDJEpEA9Y
VHHd4hXY8dD5yhAAAAGAAAAAEAAAEXAAAAB3NzaC1yc2EAAAADAQABAAABAQDlg8ho2tsN
CucL7iimU7P57OMdXsVPGnf8KdEHeX7r+1+V1KSSFPRFOPlBixsxNurtUKG7jNpvn/MqRJ
"""

# token usado por usuarios externos para accesar API
EXTERNAL_AUTH_TOKEN = "6f1a9d4b27c3e8a0f5b19c2d43e7a8d1"

# token usado por usuarions internos para accesar API
INTERNAL_AUTH_TOKEN = "xsw5R0oHBUJWJhxUqTmHdGmuYhHUNVy62bdJMPtxFjXgjdpCg5K3NgIXQkqwxCujUQ5GtC7m8GWe8JawqlOEkYdmUQLcQTLy"

TRUECAPTCHA_KEY = "UEJgzM79VWFZh6MpOJgh"
FLASK_SECRET_KEY = "aGEJcYywXbY48oxwT1fKypBnsx5z9Ji13W3bGY6xUpnZR2rHrHnIZjwCNdd1i5QhkZdhGe7vNwZwg2OvFZ14MH6AwplbghFON0VO"

GOOGLE_CLIENT_ID = ""
GOOGLE_CLIENT_SECRET = ""
GOOGLE_CALLBACK_URI = ""
FACEBOOK_CLIENT_ID = ""
FACEBOOK_CLIENT_SECRET = ""

# zeptomail
ZOHO_INFO_PASSWORD = "5QJWEKi0trAL"
ZEPTOMAIL_INFO_TOKEN = "Zoho-enczapikey wSsVR60lrkb4B/h8mmGtLutrmA5WDlzxQEwsiVGo7HKvSvrFosc/khXIBgGgT6UcGDFrQDMS9rIgyR4IgDAPjNotnAoGXiiF9mqRe1U4J3x17qnvhDzJXGxclROKKIwNwQRinmZkEs8m+g=="

# zohomail
ZOHO_MAIL_API_CLIENT_ID = "1000.400ELE5I2WU72H931RQI8HTIY2Y30E"
ZOHO_MAIL_API_CLIENT_SECRET = "fe41ea63cc1c667091b32b1068660cf0b44fffd823"

# 3-letter months
MONTHS_3_LETTERS = (
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Oct",
    "Nov",
    "Dic",
)

# scrapers headless (debugging)
HEADLESS = {
    "brevete": True,
    "satimp": True,
    "soat": True,
    "jneafil": True,
    "jnemulta": False,
    "osiptel": False,
}

# table data
SQL_TABLES = {
    "DataMtcBrevetes": "DOC",
    "DataSatImpuestosCodigos": "DOC",
    "DataSatImpuestosDeudas": "COD",
    "DataOsiptelLineas": "DOC",
    "DataMtcRecordsConductores": "DOC",
    "DataSunatRucs": "DOC",
    "DataJneMultas": "DOC",
    "DataJneAfiliaciones": "DOC",
    "DataMtcRevisionesTecnicas": "PLACA",
    "DataApesegSoats": "PLACA",
    "DataSatMultas": "PLACA",
    "DataSutranMultas": "PLACA",
    "DataSunarpFichas": "PLACA",
}
