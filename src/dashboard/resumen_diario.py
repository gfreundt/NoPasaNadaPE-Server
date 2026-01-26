import logging
from datetime import datetime as dt

from src.utils.utils import send_pushbullet

logger = logging.getLogger(__name__)


def main(self):
    try:
        cursor = self.db.cursor()

        # obtener mensajes enviados
        cursor.execute(
            """ SELECT TipoMensaje, DireccionCorreo
                    FROM StatusMensajesEnviados
                    WHERE FechaEnvio >= date('now', 'localtime', '-1 day')
                    AND FechaEnvio < date('now', 'localtime');
                """
        )

        mensajes = [
            f"{i['TipoMensaje']} - {i['DireccionCorreo']}" for i in cursor.fetchall()
        ]
        s = [f"----- MENSAJES: {len(mensajes)} -----"] + mensajes

        # obtener SUNARPS pendientes
        cursor.execute(
            """ SELECT Placa FROM InfoPlacas
                WHERE LastUpdateSunarpFichas = '2020-01-01'
            """
        )

        s += [f"----- SUNARPS: {len(cursor.fetchall())} -----"]

        activity = send_pushbullet(
            title="Status Diario " + str(dt.now())[:10], message="\n".join(s)
        )

        logger.info(f"Resumen Diario Enviado: {activity}")

    except Exception as e:
        logger.error(f"Error Resumen Diario: {e}")
