import os
import platform


# paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if platform.system() == "Linux":
    if platform.node() == "power":
        NETWORK_PATH = os.path.join("/mnt", "gce")
        NETWORK_PATH = os.path.join("/home", "gfreundt", "NoPasaNadaPE-Server")
    elif platform.node() == "nopasanada-server":
        NETWORK_PATH = os.path.join("/home", "nopasanadape", "NoPasaNadaPE-Server")
    else:
        if "-dev" in BASE_DIR:
            NETWORK_PATH = "/var/www/nopasanadape-dev/app"
        else:
            NETWORK_PATH = "/var/www/nopasanadape/app"

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
