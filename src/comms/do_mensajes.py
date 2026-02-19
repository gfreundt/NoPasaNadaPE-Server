import logging

from src.comms import generar_mensajes, enviar_mensajes
from src.updates import do_actualizar


logger = logging.getLogger(__name__)


def main(db, tipo_mensaje):

    titulo = f"[ DO MENSAJES {tipo_mensaje.upper()} ]"

    logger.info(f"{titulo} Iniciando")

    # actualizar datos
    logger.info(f"{titulo} Lanzando Actualizar Datos")
    continuar = do_actualizar.main(db, tipo_mensaje)

    # si hubieron datos actualizados correctamente: generar mensajes
    if continuar:
        logger.info(f"{titulo} Lanzando Generar Mensajes")
        if tipo_mensaje == "alertas":
            continuar = generar_mensajes.alertas(db)
        elif tipo_mensaje == "boletines":
            continuar = generar_mensajes.boletines(db)

        # hay mensajes generados - enviar mensajes
        if continuar:
            logger.info(f"{titulo} Lanzando Enviar Mensajes")
            resultado = enviar_mensajes.main(db, tipo_mensaje)

            # mensajes enviados correctamente - fin del proceso
            if resultado:
                logger.info(f"{titulo} Fin Normal del Proceso.")
                return True
            logger.warning(f"{titulo} No se Pudo Enviar Mensajes. Fin del Proceso.")

        else:
            logger.warning(
                f"{titulo} No se Completo Generar Mensajes. Fin del Proceso."
            )

    # proceso no llego al final (error actualizando, no hay nuevos mensajes generados o no se pudieron enviar)
    return False
