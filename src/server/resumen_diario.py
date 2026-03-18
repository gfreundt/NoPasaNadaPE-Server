from src.comms import enviar_correo_interno
from src.updates import datos_actualizar
from datetime import datetime as dt, timedelta as td
import shutil
from pprint import pformat
import logging

logger = logging.getLogger(__name__)


def main(db):
    """
    Genera un resumen diario y lo envia por correo:
    Contenido:
        1. Mensajes enviados el dia anterior (tipo y destinatario)
        2. SUNARPS que requieren actualizacion manual
        3. Espacio disponible en disco donde se guarda base de datos
    """

    titulo = "[RESUMEN DIARIO]"

    try:
        logger.info(f"{titulo} Inciando")

        # correr todas las partes del resumen diario y guardar resultados en una lista
        resultado = []
        resultado += mensajes_enviados_ayer(db)
        resultado += sunarps_pendientes(db)
        resultado += espacio_disco()

        logger.info(f"{titulo} {pformat(resultado)}")

        # enviar mensaje con resultado del resumen diario
        exito = enviar_correo_interno.informe_diario(
            titulo=f"Resumen Diario ({(dt.now() - td(days=1)).strftime('%Y-%m-%d')})",
            mensaje=resultado,
        )

        # logear resultados del envio
        if exito:
            logger.info(f"{titulo} Enviado ok.")
        else:
            logger.warning(f"{titulo} Error enviando.")

    except Exception:
        logger.exception(f"{titulo} Error.")


def mensajes_enviados_ayer(db):
    """
    Reporte: mensajes enviados el dia anterior (tipo y destinatario).
    """

    cmd = """ 
          SELECT TipoMensaje, DireccionCorreo
          FROM StatusMensajesEnviados
          WHERE FechaEnvio >= date('now', 'localtime', '-1 day')
            AND FechaEnvio < date('now', 'localtime');
          """
    cursor = db.cursor()
    cursor.execute(cmd)

    # elaborar mensaje, ponerle el titulo con el contador de incidencias y proyeccion estimada de mensajes que seran enviados hoy
    mensajes = [
        f"{i['TipoMensaje']} - {i['DireccionCorreo']}" for i in cursor.fetchall()
    ]
    mensajes.insert(0, f"----- MENSAJES: {len(mensajes)} -----")
    mensajes.append(
        f"Estimados Hoy: {len(datos_actualizar.get_datos_boletines(db=db, premensaje=False, ajuste=0))}"
    )
    mensajes.append(
        f"Estimados Mañana: {len(datos_actualizar.get_datos_boletines(db=db, premensaje=False, ajuste=1))}"
    )
    return mensajes


def sunarps_pendientes(db):
    """
    Reporte: SUNARPS con ultima fecha de actualizacion hace mas de un año o nunca actualizados.
             Aviso para hacer scraping manual de datos.
    """

    cmd = """
          SELECT Placa FROM InfoPlacas
          WHERE LastUpdateSunarpFichas < DATE('now', 'localtime', '-1 year')
             OR LastUpdateSunarpFichas IS NULL
          """
    cursor = db.cursor()
    cursor.execute(cmd)

    # elaborar mensaje, ponerle el titulo con el contador de incidencias
    sunarps = [f"{i['Placa']}" for i in cursor.fetchall()]
    sunarps.insert(0, f"----- SUNARPS: {len(sunarps)} -----")
    return sunarps


def espacio_disco():
    """
    Reporte: espacio disponible en disco donde se guarda base de datos.
    """

    total, used, free = shutil.disk_usage("/")
    return [
        f"----- ESPACIO EN DISCO DISPONIBLE: {free / total:.1%} -----",
        f"Total: {total / (1024**3):.2f} GB",
        f"Usado:  {used / (1024**3):.2f} GB",
        f"Libre:  {free / (1024**3):.2f} GB",
    ]
