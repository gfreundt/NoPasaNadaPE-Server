import logging

from src.comms import generar_mensajes, enviar_mensajes
from src.updates import do_actualizar

logger = logging.getLogger(__name__)


def main(db, tipo_mensaje):
    """
    Proceso principal para enviar alertas y boletines.
    Pasos:
        1. Actualizar datos (actualiza la base de datos con scrapers)
        2. Generar mensajes (a partir de datos actualizados)
        3. Enviar mensajes (a destinatarios correspondientes)
    Retorna True si el proceso se completo con exito (datos actualizados, mensajes generados y enviados),
    Retorna False si no se completo el proceso (sin actualizaciones, error actualizando, generando o enviando mensajes)
    """

    titulo = f"[ MENSAJES {tipo_mensaje.upper()} ]"

    # actualizar datos
    logger.info(f"{titulo} Paso 1: Actualizar Datos")
    continuar = do_actualizar.main(db, tipo_mensaje)
    if not continuar:
        logger.info(f"{titulo} Actualizar Datos: Fin del Proceso.")
        return False

    # generar mensajes
    logger.info(f"{titulo} Paso 2: Generar Mensajes")
    if tipo_mensaje == "alertas":
        continuar = generar_mensajes.alertas(db)
    elif tipo_mensaje == "boletines":
        continuar = generar_mensajes.boletines(db)
    if not continuar:
        logger.warning(f"{titulo} Generar Mensajes: Fin del Proceso.")
        return False

    # enviar mensajes
    logger.info(f"{titulo} Paso 3: Enviar Mensajes")
    continuar = enviar_mensajes.main(db, tipo_mensaje)
    if not continuar:
        logger.warning(f"{titulo} Enviar Mensajes: Fin del Proceso.")
        return False

    # fin normal del proceso (con todos los pasos cumplidos)
    logger.info(f"{titulo} Fin Normal del Proceso.")
    return True
