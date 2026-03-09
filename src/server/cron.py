import schedule
import threading
import time
import sys
import logging

from src.utils.constants import AMBIENTE_PRODUCCION
from src.server import resumen_diario, mantenimiento, prueba_scrapers
from src.comms import do_mensajes

logger = logging.getLogger(__name__)


def job_seguro(fn, *args, **kwargs):
    """
    Ejecuta un job de forma segura para que una excepcion no detenga todo el scheduler.
    """

    try:
        fn(*args, **kwargs)
    except Exception:
        logger.warning(
            f"Error ejecutando job dentro de cron: {fn.__name__}", exc_info=True
        )


def ejecutar_scheduler(db):
    """
    Ejecuta las tareas programadas dentro de un wrapper para que fallos en tareas individuales no detengan el scheduler.
    Tareas programadas:
        1. Boletines a las hh:05 entre 7am y 8pm (inclusive)
        2. Alertas dos veces al dia (8:30am y 3:30pm)
        3. Resumen diario (del dia anterior), diariamente a la 1am
        4. Prueba de scrapers diariamente a las 6:30am
        5. Mantenimiento (cada hora) a las hh:45
        6. Mantenimiento (cada dia) a las 02:05am
    """

    # 1. Boletines a las hh:05 entre 7am y 8pm (inclusive)
    for hour in range(7, 21):
        schedule.every().day.at(f"{hour:02d}:05").do(
            job_seguro, do_mensajes.main, db, "boletines"
        ).tag("boletines")

    # 2. Alertas dos veces al dia (8:30am y 3:30pm)
    schedule.every().day.at("08:30").do(
        job_seguro, do_mensajes.main, db, "alertas"
    ).tag("alertas")
    schedule.every().day.at("15:30").do(
        job_seguro, do_mensajes.main, db, "alertas"
    ).tag("alertas")

    # 3. Resumen diario (del dia anterior), diariamente a la 1am
    schedule.every().day.at("01:00").do(job_seguro, resumen_diario.main, db).tag(
        "resumen_diario"
    )

    # 4. Prueba de scrapers diariamente a las 6:30am
    schedule.every().day.at("06:30").do(job_seguro, prueba_scrapers.main).tag(
        "prueba_scrapers"
    )

    # 5. Mantenimiento (cada hora) a las hh:45
    for hour in range(0, 24):
        schedule.every().day.at(f"{hour:02d}:45").do(
            job_seguro, mantenimiento.cada_hora, db
        ).tag("mantenimiento_horario")

    # 6. Mantenimiento (cada dia) a las 02:05am
    schedule.every().day.at("02:05").do(job_seguro, mantenimiento.cada_dia, db).tag(
        "mantenimiento_diario"
    )

    # logger output
    logger.info(
        f"Cron scheduler iniciado. Tareas programadas: {len(schedule.get_jobs())}"
    )
    for job in sorted(schedule.get_jobs(), key=lambda j: j.next_run)[:10]:
        logger.info(f"Siguiente Tarea: {job.next_run} -> {job.tags}")

    # activar schedule (loop infinito con pausa de 10 segundos entre chequeos)
    while True:
        schedule.run_pending()
        time.sleep(10)


def main(db):
    """
    Crea un thread que controla los procesos que se ejecutan de forma automatica segun horarios.
    """

    # SOLO PARA PRUEBAS: ejecutar script de prueba de scrapers y salir
    if "TEST" in sys.argv:
        from src.test import test_script_from_cron

        test_script_from_cron.main(db)
        return

    if not AMBIENTE_PRODUCCION:
        logger.warning("AMBIENTE_PRODUCCION no esta activo, cron no se iniciara")
        return

    logger.info("Iniciando cron en master worker")
    t = threading.Thread(
        target=ejecutar_scheduler,
        args=(db,),
        daemon=True,
    )
    t.start()
