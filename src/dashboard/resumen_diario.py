from src.comms import enviar_correo_interno
from datetime import datetime as dt
import shutil
import logging

logger = logging.getLogger(__name__)


def main(self):
    try:
        cursor = self.db.cursor()

        titulo = f"Resumen Diario ({str(dt.now())[:19]})"

        resultado = []
        resultado += mensajes_enviados_ayer(cursor)
        resultado += sunarps_pendientes(cursor)
        resultado += espacio_disco()

        enviar_correo_interno.informe_diario(cursor, titulo=titulo, mensaje=resultado)

    except Exception as e:
        logger.error(f"Error Resumen Diario: {e}")


def mensajes_enviados_ayer(cursor):
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
    mensajes.insert(0, f"----- MENSAJES: {len(mensajes)} -----")

    return mensajes


def sunarps_pendientes(cursor):
    # obtener SUNARPS con ultima fecha de actualizacion hace mas de un año (incluye los nuevos nunca actualizados)
    cursor.execute(
        """ SELECT Placa FROM InfoPlacas
                    WHERE LastUpdateSunarpFichas < DATE('now', 'localtime', '-1 year')
        """
    )

    sunarps = [f"{i['Placa']}" for i in cursor.fetchall()]
    sunarps.insert(0, f"----- SUNARPS: {len(sunarps)} -----")

    return sunarps


def espacio_disco():
    # calcular el espacio disponible en disco donde se guarda base de datos

    total, used, free = shutil.disk_usage("/")

    return [
        f"----- ESPACIO EN DISCO: {free / total:.1%} -----",
        f"Total: {total / (1024**3):.2f} GB",
        f"Used:  {used / (1024**3):.2f} GB",
        f"Free:  {free / (1024**3):.2f} GB",
    ]
