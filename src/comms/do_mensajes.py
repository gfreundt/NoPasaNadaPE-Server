from src.comms import generar_mensajes, enviar_mensajes
from src.updates import do_actualizar
import logging

logger = logging.getLogger(__name__)


def main(self, tipo_mensaje):

    titulo = f"[ DO MENSAJES {tipo_mensaje.upper()} ]"

    logger.info(f"{titulo} Iniciando")

    # no activar si el switch de autoscraper esta apagado
    if not self.config_autoscraper:
        logger.warning(f"{titulo} OFFLINE")
        self.log(action=f"{titulo} OFFLINE")
        return False

    # actualizar datos
    logger.info(f"{titulo} Lanzando Actualizar Datos")
    resultado = do_actualizar.main(self, tipo_mensaje)

    # datos actualizados correctamente: generar mensajes
    if resultado:
        logger.info(f"{titulo} Lanzando Generar Mensajes")
        if tipo_mensaje == "alertas":
            resultado = generar_mensajes.alertas(self)
        elif tipo_mensaje == "boletines":
            resultado = generar_mensajes.boletines(self)

        # hay mensajes generados - enviar mensajes
        if resultado:
            logger.info(f"{titulo} Lanzando Enviar Mensajes")
            resultado = enviar_mensajes.main(self, tipo_mensaje)

            # mensajes enviados correctamente - fin del proceso
            if resultado:
                logger.info(f"{titulo} Fin Normal del Proceso.")
                return True
            logger.warning(f"{titulo} No se Pudo Enviar Mensajes. Fin del Proceso.")

        else:
            logger.warning(
                f"{titulo} No se Completo Generar Mensajes. Fin del Proceso."
            )

    else:
        logger.warning(f"{titulo} No se Completo Actualizar Datos. Fin del Proceso.")

    # proceso no llego al final (error actualizando, no hay nuevos mensajes generados o no se pudieron enviar)
    return False
