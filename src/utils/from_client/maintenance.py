import os
from src.utils.constants import NETWORK_PATH


def clear_outbound_folder(tipo=None):
    """
    borra todos los archivos de /outbound que cumplan con formato indicado
    default: todas las alertas y boletines
    """

    # en caso no se pasan parametros, usar default
    if not tipo:
        tipo = ("alerta", "boletin")

    # si solo tiene un string, convertir a lista
    if isinstance(tipo, str):
        tipo_archivos = [tipo]

    for file in os.listdir(os.path.join(NETWORK_PATH, "outbound")):
        for tipo_archivo in tipo_archivos:
            if tipo_archivo in file:
                os.remove(os.path.join(NETWORK_PATH, "outbound", file))


def pre():

    security_folder = os.path.join(NETWORK_PATH, "security")
    update_files = [i for i in os.listdir(security_folder) if "update_" in i]

    # borrar todos los backups de updates excepto los ultimos 15
    for file in update_files[:-15]:
        os.remove(os.path.join(NETWORK_PATH, "security", file))
