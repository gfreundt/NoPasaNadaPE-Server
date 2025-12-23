import os
import platform

# administrables
GATHER_ITERATIONS = 4
AUTOSCRAPER_REPETICIONES = 3


IPS_CONOCIDOS = {
    "AR": [],
    "PE": ["95.173.223.116"],
    "US": ["72.60.155.196"],
}

# paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if platform.system() == "Linux":
    CHROMEDRIVER_PATH = r"/usr/local/bin/chromedriver"
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
    CHROMEDRIVER_PATH = r"src\chromedriver.exe"
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
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)

MESES_NOMBRE_COMPLETO = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
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
    "DataCallaoMultas": "PLACA",
}

FORMATO_PASSWORD = {
    "regex": r"^(?=.*[A-Z]).{6,}",
    "mensaje": "Contraseña debe tener mínimo 6 caracteres e incluir una mayúscula.",
}


# scrapers headless (debugging)
HEADLESS = {
    "brevetes": True,
    "satimp": True,
    "soat": True,
    "jneafil": True,
    "jnemulta": True,
    "osiptel": True,
    "satmul": True,
    "recvehic": True,
    "revtec": True,
    "sunarp": False,
    "sunat": True,
    "sutran": True,
    "calmul": True,
}

# nombre de tablas
TABLAS_BD = {
    "DataMtcRecordsConductores",
    "DataMtcBrevetes",
    "DataSatMultas",
    "DataSatImpuestos",
    "DataMtcRevisionesTecnicas",
    "DataSutranMultas",
    "DataSunarpFichas",
    "DataApesegSoats",
    "DataCallaoMultas",
}


SCRAPER_TIMEOUT = {
    "brevetes": 60,
    "satimps": 60,
    "soat": 60,
    "jneafil": True,
    "jnemulta": True,
    "osiptel": True,
    "satmuls": 240,
    "recvehic": 60,
    "revtec": 60,
    "sunarps": 60,
    "sunat": True,
    "sutrans": 60,
    "calmul": 90,
}

DASHBOARD_URL = "cc1c667091b8GWe8JawqlOEkY11af6ff2e"

# aseguradora info
ASEGURADORAS = {
    "Interseguro": "(01) 500 - 0000",
    "Rimac Seguros": "(01) 615 - 1515",
    "Pacifico Seguros": "(01) 415 - 1515",
    "La Positiva": "(01)  211 - 0211",
    "Mapfre Perú": "(01)  213 - 3333",
    "Protecta": "(01) 391 - 3000",
    "Vivir Seguros": "(01) 604 - 2000",
}

MTC_CAPTCHAS = {
    "anillo": 1,
    "arbol": 2,
    "carro": 3,
    "avion": 4,
    "bicicleta": 5,
    "billetera": 6,
    "botella": 7,
    "camion": 8,
    "cinturon": 9,
    "desarmador": 10,
    "edificio": 11,
    "gafas": 12,
    "gato": 13,
    "laptop": 14,
    "linterna": 15,
    "llaves": 16,
    "manzana": 17,
    "media": 18,
    "mesa": 19,
    "mochila": 20,
    "perro": 21,
    "pez": 22,
    "pinia": 23,
    "platano": 24,
    "puerta": 25,
    "reloj": 26,
    "scooter": 27,
    "silla": 28,
    "tasa": 29,
    "tienda": 30,
    "timon": 31,
    "zapato": 32,
}
