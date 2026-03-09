import random
import os
import json
from src.utils.constants import NETWORK_PATH
from src.scrapers import configuracion_scrapers


def get_test_data():

    config = configuracion_scrapers.config()
    with open(os.path.join(NETWORK_PATH, "static", "test_data.json", "r")) as file:
        data_cruda = json.load(file)

    data = []
    for key in config.keys():
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
