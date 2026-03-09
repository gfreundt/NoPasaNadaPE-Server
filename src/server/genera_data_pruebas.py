import random
import os
import json
from src.utils.constants import NETWORK_PATH
from src.scrapers import configuracion_scrapers


def generar(tamano_muestra=1):
    """
    Genera data de pruebas estructurada para ser enviada a scrapers con 'tamaño_muestra' registros por scraper.
    Extrae datos al azar de "./static/data_pruebas.json"
    Solamente si el scraper esta activo activo en configuracion de scrapers.
    """

    config = configuracion_scrapers.config()
    with open(os.path.join(NETWORK_PATH, "static", "data_pruebas.json"), "r") as file:
        data_cruda = json.load(file)["data"]

    data = []
    for key in config.keys():
        for _ in range(tamano_muestra):
            dato = random.choice(data_cruda)
            if config[key]["activo"]:
                data.append(
                    {
                        "Categoria": key,
                        "IdMember": dato[0],
                        "DocTipo": dato[1],
                        "DocNum": dato[2],
                        "Placa": dato[3],
                    }
                )

    return data
