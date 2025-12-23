import time
from datetime import datetime as dt, timedelta as td
import os
import json
import atexit
import queue
from threading import Thread, Lock
from src.server import do_updates
from src.utils.constants import NETWORK_PATH, GATHER_ITERATIONS
from src.utils.utils import vpn_online, start_vpn, stop_vpn, get_public_ip


# local imports
from src.updates import (
    gather_brevetes,
    gather_revtecs,
    gather_sutrans,
    gather_satimps,
    gather_recvehic,
    gather_sunarps,
    gather_satmuls,
    gather_soats,
    gather_calmul,
)

# TODO: find a jnemultas with actual multas


def gather_threads(dash, all_updates):

    # # TESTING: brevetes, recvehic, revtecs, satimps, satmuls, soats, sunarps, sutrans, calmul
    # from src.test.test_data import get_test_data
    # all_updates = get_test_data([3, 3, 3, 3, 3, 3, 3, 0, 3])
    # all_updates = get_test_data([0, 0, 2, 0, 0, 0, 0, 0, 0])

    # log change of dashboard status
    dash.log(general_status=("Activo", 1))
    dash.scrapers_corriendo = True

    lock = Lock()
    vpn_pe_threads = []
    vpn_ar_threads = []
    full_response = {}
    atexit.register(update_local_gather_file, full_response)
    atexit.register(stop_vpn)

    # records vehiculares
    if all_updates.get("DataMtcRecordsConductores"):
        vpn_ar_threads.append(
            Thread(
                target=manage_sub_threads,
                args=(
                    dash,
                    lock,
                    all_updates["DataMtcRecordsConductores"],
                    full_response,
                    gather_recvehic,
                    "DataMtcRecordsConductores",
                ),
            )
        )

    # brevetes
    if all_updates.get("DataMtcBrevetes"):
        vpn_ar_threads.append(
            Thread(
                target=manage_sub_threads,
                args=(
                    dash,
                    lock,
                    all_updates["DataMtcBrevetes"],
                    full_response,
                    gather_brevetes,
                    "DataMtcBrevetes",
                ),
            )
        )

    # multas sat
    if all_updates.get("DataSatMultas"):
        vpn_pe_threads.append(
            Thread(
                target=manage_sub_threads,
                args=(
                    dash,
                    lock,
                    all_updates["DataSatMultas"],
                    full_response,
                    gather_satmuls,
                    "DataSatMultas",
                ),
            )
        )

    # revisiones tecnicas
    if all_updates.get("DataMtcRevisionesTecnicas"):
        vpn_pe_threads.append(
            Thread(
                target=manage_sub_threads,
                args=(
                    dash,
                    lock,
                    all_updates["DataMtcRevisionesTecnicas"],
                    full_response,
                    gather_revtecs,
                    "DataMtcRevisionesTecnicas",
                ),
            )
        )

    # multas sutran
    if all_updates.get("DataSutranMultas"):
        vpn_pe_threads.append(
            Thread(
                target=manage_sub_threads,
                args=(
                    dash,
                    lock,
                    all_updates["DataSutranMultas"],
                    full_response,
                    gather_sutrans,
                    "DataSutranMultas",
                ),
            )
        )

    # impuestos sat
    if all_updates.get("DataSatImpuestos"):
        vpn_pe_threads.append(
            Thread(
                target=gather_satimps.manage_sub_threads,
                args=(
                    dash,
                    lock,
                    all_updates["DataSatImpuestos"],
                    full_response,
                ),
            )
        )

    # fichas sunarp
    if all_updates.get("DataSunarpFichas"):
        vpn_pe_threads.append(
            Thread(
                target=manage_sub_threads,
                args=(
                    dash,
                    lock,
                    all_updates["DataSunarpFichas"],
                    full_response,
                    gather_sunarps,
                    "DataSunarpFichas",
                ),
            )
        )

    # soat (los primeros 12 con un vpn, los otros 12 con otro vpn)
    if all_updates.get("DataApesegSoats"):
        vpn_pe_threads.append(
            Thread(
                target=manage_sub_threads,
                args=(
                    dash,
                    lock,
                    all_updates["DataApesegSoats"][:12],
                    full_response,
                    gather_soats,
                    "DataApesegSoats",
                ),
            )
        )

    if all_updates.get("DataApesegSoats") and len(all_updates["DataApesegSoats"]) > 12:
        vpn_ar_threads.append(
            Thread(
                target=manage_sub_threads,
                args=(
                    dash,
                    lock,
                    all_updates["DataApesegSoats"][12:24],
                    full_response,
                    gather_soats,
                    "DataApesegSoats",
                ),
            )
        )

    # callao multas
    if all_updates.get("DataCallaoMultas"):
        vpn_pe_threads.append(
            Thread(
                target=manage_sub_threads,
                args=(
                    dash,
                    lock,
                    all_updates["DataCallaoMultas"],
                    full_response,
                    gather_calmul,
                    "DataCallaoMultas",
                ),
            )
        )

    for thread_group, pais in zip((vpn_pe_threads, vpn_ar_threads), ("pe", "ar")):

        if not thread_group:
            continue

        # inicia la VPN en el pais que corresponde
        exito = start_vpn(pais)
        if not exito:
            dash.log(action="Failed VPN")
            return

        dash.log(action="Nuevo IP: " + get_public_ip())

        with lock:
            dash.data["scrapers_kpis"].update(
                {
                    "extra": {
                        "status": f"ACTIVO VPN: {pais}",
                    }
                }
            )

        # iniciar threads con intervalos para que subthreads puedan iniciar sin generar conflictos
        for thread in thread_group:
            thread.start()
            time.sleep(2 * GATHER_ITERATIONS)

        # se queda en esta seccion hasta que todos los threads hayan terminado
        start_time = time.perf_counter()
        while any(t.is_alive() for t in thread_group):

            time.sleep(10)

            # grabar cada 90 segundos lo que este en memoria de respuestas
            if time.perf_counter() - start_time > 90:
                update_local_gather_file(full_response)
                start_time = time.perf_counter()

        with lock:
            dash.data["scrapers_kpis"].update(
                {
                    "extra": {
                        "status": "INACTIVO",
                    }
                }
            )

        # detiene la VPN
        stop_vpn()
        time.sleep(5)

    # actualiza el archivo local que guarda la data de actualizaciones (solo debug)
    dash.scrapers_corriendo = False
    update_local_gather_file(full_response)

    # actualiza base de datos con todo lo obtenido
    dash.log(general_status=("Esperando", 2))
    do_updates.main(db=dash.db, data=full_response)

    # devuelve dato del tamaño de los datos actualizados en Kb (solo referencia)
    return f"{len(json.dumps(full_response).encode("utf-8")) / 1024:.3f}"


def manage_sub_threads(
    dash,
    lock,
    update_data,
    full_response,
    target_func,
    update_key,
):

    # create variable that accumulates all sub-thread responses
    local_response = []
    full_response[update_key] = local_response
    total_inicial = len(update_data)

    # load queue with data that needs to be updated
    queue_update_data = queue.Queue()
    for item in update_data:
        queue_update_data.put(item)

    # launch and join N sub-threads for the main thread, report scraper as active in dashboard
    with lock:
        dash.data["scrapers_kpis"].update(
            {
                update_key: {
                    "status": "ACTIVO",
                }
            }
        )

    start_time = start_time1 = start_time2 = time.perf_counter()
    threads = []

    # abre un maximo de scrapers paralelos del mismo servicio (no mayor a la cantidad de datos a actualizar)
    for i in range(min(GATHER_ITERATIONS, len(update_data))):

        # asignar siguiente trabajador disponible
        siguiente_trabajador = 0
        while siguiente_trabajador in dash.assigned_cards:
            siguiente_trabajador += 1
        dash.assigned_cards.append(siguiente_trabajador)

        # crear subthread
        thread = Thread(
            target=target_func.gather,
            args=(
                dash,
                queue_update_data,
                local_response,
                len(update_data),
                lock,
                siguiente_trabajador,
                i,
            ),
            name=f"{target_func}-{i}",
        )
        thread.start()
        threads.append(thread)

        # escalonar inicio
        time.sleep(1.5)

    # wait for all active threads to finish, in the meantime perfom updates every n seconds
    active_threads = 1
    while active_threads > 0:

        active_threads = sum(1 for thread in threads if thread.is_alive())

        # grabar lo que se tiene en memoria hasta el momento en un archivo cada 90 segundos
        if time.perf_counter() - start_time1 > 90:
            start_time1 = time.perf_counter()
            with lock:
                update_local_gather_file(full_response)

        # actualizar status de scrapers cada segundo
        if time.perf_counter() - start_time2 > 1:
            start_time2 = time.perf_counter()
            with lock:
                # pendientes
                dash.data["scrapers_kpis"][update_key].update(
                    {"pendientes": queue_update_data.qsize()}
                )
                # threads activas
                dash.data["scrapers_kpis"][update_key].update(
                    {"threads_activos": active_threads}
                )
                # eta
                tiempo_restante = (
                    (time.perf_counter() - start_time) / total_inicial
                ) * queue_update_data.qsize()
                dash.data["scrapers_kpis"][update_key].update(
                    {
                        "eta": dt.strftime(
                            dt.now() + td(seconds=tiempo_restante), "%H:%M:%S"
                        )
                    }
                )
                # fila de acumulado
                dash.data["scrapers_kpis"]["Acumulado"]["status"] = "INACTIVOXX"
                dash.data["scrapers_kpis"]["Acumulado"]["pendientes"] = 120
                dash.data["scrapers_kpis"]["Acumulado"]["eta"] = dt.strftime(
                    dt.now() + td(seconds=102), "%H:%M:%S"
                )
                dash.data["scrapers_kpis"]["Acumulado"]["threads_activos"] = 99

        time.sleep(0.5)

    # put all respones into global collector variable and switch dashboard status to inactive
    with lock:
        dash.data["scrapers_kpis"].update(
            {update_key: {"status": "INACTIVO", "eta": "", "threads_activos": ""}}
        )
    full_response.update({update_key: local_response})


def update_local_gather_file(full_response):
    update_files = [
        int(i[-10:-5])
        for i in os.listdir(os.path.join(NETWORK_PATH, "security"))
        if "update_" in i
    ]
    if not update_files:
        next_secuential = 0
    else:
        next_secuential = max(update_files) + 1

    with open(
        os.path.join(NETWORK_PATH, "security", f"update_{next_secuential:05d}.json"),
        mode="w",
    ) as outfile:
        outfile.write(json.dumps(full_response))
