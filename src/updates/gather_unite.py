import time
from datetime import datetime as dt, timedelta as td
import os
import json
import atexit
import queue
from threading import Thread, Lock
from func_timeout import exceptions
from copy import deepcopy as copy
import io
import base64

from src.scrapers.scraper_configurations import SCRAPER_CONFIGS
from src.utils.constants import HEADLESS, GATHER_ITERATIONS, NETWORK_PATH, ASEGURADORAS
from src.utils.webdriver import ChromeUtils
from src.utils.utils import date_to_db_format


# --- Helper Functions (From individual files) ---


def update_local_gather_file(full_response):
    """Saves the current response data to a JSON file (From gather_all.py)."""
    # NOTE: This uses NETWORK_PATH from constants, assumed available.
    if not full_response:
        return
    update_files = [
        int(i[-10:-5])
        for i in os.listdir(os.path.join(NETWORK_PATH, "security"))
        if "update_" in i
    ]
    next_secuential = max(update_files) + 1 if update_files else 1
    os.makedirs(os.path.join(NETWORK_PATH, "security"), exist_ok=True)
    with open(
        os.path.join(NETWORK_PATH, "security", f"update_{next_secuential:05d}.json"),
        mode="w",
    ) as outfile:
        outfile.write(json.dumps(full_response, indent=4))


# --- Core Gathering Logic (Consolidated from all gather_*.py files) ---


def gather_subthread(
    config_key,
    dash,
    queue_update_data,
    local_response,
    total_original,
    lock,
    card,
    subthread,
):
    """The core logic for a single scraping subthread."""
    config = SCRAPER_CONFIGS[config_key]
    headless_key = config["headless_key"]
    scraper_module = config["scraper"]
    is_member_data = config.get("is_member_data", False)
    response_handler = config["response_handler"]
    skip_if_captcha = config.get("skip_response_if_captcha", False)

    # Build webdriver (customized for Sunarp/SOAT/SATMUL if needed, defaulting to generic)
    incognito = False
    window_size = None
    if config_key in ["sunarps", "satmuls", "soats"]:
        incognito = True
        window_size = (1920, 1080)

    chromedriver = ChromeUtils(
        headless=HEADLESS[headless_key],
        incognito=incognito,
        window_size=window_size,
    )
    webdriver = chromedriver.direct_driver()
    same_ip_scrapes = 0  # Only relevant for SOAT, but harmless elsewhere

    # Initialize ETA variables
    tiempo_inicio = time.perf_counter()
    procesados = 0
    eta = 0

    while True:
        record_item = None
        try:
            record_item = queue_update_data.get_nowait()
            if is_member_data:
                id_member, doc_tipo, doc_num = record_item
                log_item = f"{doc_tipo} {doc_num}"
            else:
                placa = record_item
                log_item = placa

        except queue.Empty:
            dash.log(
                card=card,
                title=f"{config_key.upper()}-{subthread} [PROCESADOS: {procesados}]",
                status=3,
                text="Inactivo",
                lastUpdate=f"Fin: {dt.strftime(dt.now(),'%H:%M:%S')}",
            )
            break

        # Log start
        dash.log(
            card=card,
            title=f"{config_key.upper()}-{subthread} [Pendientes: {total_original-procesados}]",
            status=1,
            text=f"Procesando: {log_item}",
            lastUpdate=f"ETA: {eta}",
        )

        try:
            # Handle special case for SUNARPS captcha-skip logic
            if config_key == "sunarps" and skip_if_captcha:
                # This is the original sunarps logic to skip processing due to persistent captcha,
                # adding an empty response and continuing.
                with lock:
                    local_response.append({"Empty": True, "PlacaValidate": record_item})
                dash.log(action=f"[ {config_key.upper()} ] {log_item}")
                continue  # Skip actual scraping and go to next item

            # Handle special case for SOAT IP restart logic
            if config_key == "soats" and same_ip_scrapes > 10:
                webdriver.quit()
                webdriver = chromedriver.direct_driver()
                same_ip_scrapes = 0

            # Execute scraper
            if is_member_data:
                # Assuming all member data scrapers have 'doc_num' and 'webdriver', and some take 'lock'
                kwargs = {"doc_num": doc_num, "webdriver": webdriver}
                if config_key == "recvehic":
                    kwargs["lock"] = lock  # Only recvehic had lock in browser_wrapper
                scraper_response = scraper_module.browser_wrapper(**kwargs)
            else:
                # Assuming all vehicle data scrapers have 'placa' and 'webdriver'
                scraper_response = scraper_module.browser_wrapper(
                    placa=placa, webdriver=webdriver
                )

            procesados += 1
            if config_key == "soats":
                same_ip_scrapes += 1

            # Handle scraper errors (string response < 100)
            if isinstance(scraper_response, str) and len(scraper_response) < 100:
                dash.log(card=card, status=2, lastUpdate=f"ERROR: {scraper_response}")
                if record_item is not None:
                    queue_update_data.put(record_item)

                if "@" in scraper_response:  # Error allows restart
                    dash.log(card=card, text="Reinicio en 10 segundos", status=1)
                    time.sleep(10)
                    continue

                break  # Non-restarting error, exit thread

            # Handle empty response
            if not scraper_response:
                empty_response = {"Empty": True}
                if is_member_data:
                    empty_response["IdMember_FK"] = id_member
                else:
                    empty_response["PlacaValidate"] = placa

                with lock:
                    local_response.append(empty_response)
                dash.log(action=f"[ {config_key.upper()} ] {log_item}")
                continue

            # Process and store successful response
            response_data = []

            # Special handling for SATIMPS (it updates two lists)
            if config_key == "satimps":
                _now = dt.now().strftime("%Y-%m-%d")
                local_response_codigos, local_response_deudas = local_response

                for _n in scraper_response:
                    with lock:
                        local_response_codigos.append(
                            {
                                "IdMember_FK": id_member,
                                "Codigo": _n["codigo"],
                                "LastUpdate": _now,
                            }
                        )
                    if _n["deudas"]:
                        for deuda in _n["deudas"]:
                            with lock:
                                local_response_deudas.append(
                                    {
                                        "Codigo": _n["codigo"],
                                        "Ano": deuda[0],
                                        "Periodo": deuda[1],
                                        "DocNum": deuda[2],
                                        "TotalAPagar": deuda[3],
                                        "FechaHasta": deuda[4],
                                        "LastUpdate": _now,
                                    }
                                )
                    else:
                        with lock:
                            local_response_deudas.append(
                                {"Empty": True, "Codigo": _n["codigo"]}
                            )

                response_data = (
                    []
                )  # No need to append to local_response later, already done with lock

            # Standard processing via response_handler
            else:
                # Apply date formatting if needed (used by brevetes, revtecs, satmuls, soats, sutrans)
                response_to_process = scraper_response
                if config_key in ["brevetes", "revtecs", "satmuls", "soats", "sutrans"]:
                    response_to_process = date_to_db_format(data=scraper_response)

                if is_member_data:
                    final_data = response_handler(
                        record_item, response_to_process, id_member
                    )
                else:
                    final_data = response_handler(
                        record_item, response_to_process, placa
                    )

                # The handler might return a list (e.g., satmuls, sutrans) or a dict (others)
                response_data = (
                    final_data if isinstance(final_data, list) else [final_data]
                )

                with lock:
                    local_response.extend(response_data)

            # Calculate ETA
            duracion_promedio = (time.perf_counter() - tiempo_inicio) / procesados
            eta = dt.strftime(
                dt.now()
                + td(seconds=duracion_promedio * (total_original - procesados)),
                "%H:%M:%S",
            )

            dash.log(action=f"[ {config_key.upper()} ] {log_item}")

        except KeyboardInterrupt:
            quit()

        except exceptions.FunctionTimedOut:
            if record_item is not None:
                queue_update_data.put(record_item)
            dash.log(card=card, status=2, lastUpdate="ERROR: Timeout")
            break

        except Exception as e:
            if record_item is not None:
                queue_update_data.put(record_item)
            dash.log(card=card, text=f"Crash (Gather): {str(e)[:55]}", status=2)
            break

    # sacar worker de lista de activos cerrar driver
    dash.assigned_cards.remove(card)
    webdriver.quit()


def manage_sub_threads(
    dash, lock, update_data, full_response, config_key, iterations=None
):
    """Manages the creation and lifecycle of sub-threads for a single scraper type."""

    total_inicial = len(update_data)

    # Special handling for SATIMPS (requires two response lists)
    if config_key == "satimps":
        local_response_codigos, local_response_deudas = [], []
        local_response = (local_response_codigos, local_response_deudas)
        full_response["DataSatImpuestosCodigos"] = local_response_codigos
        full_response["DataSatImpuestosDeudas"] = local_response_deudas
    else:
        local_response = []
        full_response[SCRAPER_CONFIGS[config_key]["update_key"]] = local_response

    # Load queue
    queue_update_data = queue.Queue()
    for item in update_data:
        queue_update_data.put(item)

    # Log status active
    with lock:
        dash.data["scrapers_kpis"].update(
            {SCRAPER_CONFIGS[config_key]["update_key"]: {"status": "ACTIVO"}}
        )

    start_time = start_time1 = start_time2 = time.perf_counter()
    threads = []

    # Determine max threads
    max_threads = iterations or max(
        GATHER_ITERATIONS, 1
    )  # Fallback to 1 if GATHER_ITERATIONS is not defined or 0
    max_threads = min(
        max_threads, total_inicial
    )  # Never more threads than items to process

    # Launch sub-threads
    for i in range(max_threads):
        # Assign next available worker card
        siguiente_trabajador = 0
        while siguiente_trabajador in dash.assigned_cards:
            siguiente_trabajador += 1
        dash.assigned_cards.append(siguiente_trabajador)

        thread = Thread(
            target=gather_subthread,
            args=(
                config_key,
                dash,
                queue_update_data,
                local_response,
                total_inicial,
                lock,
                siguiente_trabajador,
                i,
            ),
            name=f"{config_key}-{i}",
        )
        thread.start()
        threads.append(thread)
        time.sleep(1.5)  # Stagger start

    # Wait for all threads to finish
    active_threads = 1
    while active_threads > 0:

        active_threads = sum(1 for thread in threads if thread.is_alive())

        if time.perf_counter() - start_time1 > 90:  # Periodic save
            start_time1 = time.perf_counter()
            with lock:
                update_local_gather_file(full_response)

        if time.perf_counter() - start_time2 > 1:  # Dashboard KPI update
            start_time2 = time.perf_counter()
            with lock:
                update_key = SCRAPER_CONFIGS[config_key]["update_key"]
                dash.data["scrapers_kpis"][update_key].update(
                    {"pendientes": queue_update_data.qsize()}
                )
                dash.data["scrapers_kpis"][update_key].update(
                    {"threads_activos": active_threads}
                )
                tiempo_restante = (
                    (time.perf_counter() - start_time)
                    / (total_inicial - queue_update_data.qsize() or 1)
                ) * queue_update_data.qsize()
                dash.data["scrapers_kpis"][update_key].update(
                    {
                        "eta": dt.strftime(
                            dt.now() + td(seconds=tiempo_restante), "%H:%M:%S"
                        )
                    }
                )
        time.sleep(2)

    # Final log and update
    with lock:
        update_key = SCRAPER_CONFIGS[config_key]["update_key"]
        dash.data["scrapers_kpis"].update(
            {update_key: {"status": "INACTIVO", "eta": "", "threads_activos": ""}}
        )
    # The response is already in full_response due to the list/tuple reference, but we update the dict for completeness
    if config_key != "satimps":
        full_response.update({update_key: local_response})


# --- Main Dispatcher (From gather_all.py) ---


def gather_threads(dash, all_updates):
    """Main function to launch and manage all scraping processes."""

    dash.log(general_status=("Activo", 1))

    lock = Lock()
    all_threads = []
    full_response = {}
    atexit.register(update_local_gather_file, full_response)

    # Create threads for each available update type
    for key, config in SCRAPER_CONFIGS.items():
        if all_updates.get(key):
            # Special case for SATIMPS (uses its own manager structure in the original)
            if key == "satimps":
                # Call the unified manage_sub_threads which now handles SATIMPS's dual-list requirement
                all_threads.append(
                    Thread(
                        target=manage_sub_threads,
                        args=(dash, lock, all_updates[key], full_response, key),
                    )
                )
            else:
                # Standard thread creation
                iterations = config.get("iterations")
                all_threads.append(
                    Thread(
                        target=manage_sub_threads,
                        args=(
                            dash,
                            lock,
                            all_updates[key],
                            full_response,
                            key,
                            iterations,
                        ),
                    )
                )

    # Log status and start threads
    with lock:
        dash.data["scrapers_kpis"].update({"extra": {"status": "ACTIVO"}})

    for thread in all_threads:
        thread.start()
        time.sleep(2 * GATHER_ITERATIONS)  # Stagger start of main scraper types

    # Periodic saving loop
    start_time = time.perf_counter()
    while any(t.is_alive() for t in all_threads):
        time.sleep(10)
        if time.perf_counter() - start_time > 90:
            update_local_gather_file(full_response)
            start_time = time.perf_counter()

    # Final log updates
    with lock:
        dash.data["scrapers_kpis"].update({"extra": {"status": "INACTIVO"}})
    dash.log(general_status=("Esperando", 2))

    # Final save and return
    update_local_gather_file(full_response)
    return full_response


# Example usage (needs mock for dash, GATHER_ITERATIONS, etc. to run)
# if __name__ == "__main__":
#     # Mock setup for testing
#     class MockDash:
#         def __init__(self):
#             self.data = {"scrapers_kpis": {}}
#             self.assigned_cards = []
#         def log(self, *args, **kwargs):
#             # print(f"DASH LOG: {kwargs}")
#             pass
#
#     # Mock data
#     MOCK_DASH = MockDash()
#     MOCK_UPDATES = {
#         "brevetes": [(1, 'DNI', '12345678'), (2, 'DNI', '87654321')],
#         "soats": ['ABC000', 'AAA000'], # AAA000 is set to mock a specific success path
#         "satimps": [(10, 'RUC', '20123456789'), (11, 'DNI', '11111111')]
#     }
#     GATHER_ITERATIONS = 2
#     NETWORK_PATH = os.getcwd() # Use current directory for mock file save
#
#     # Run the unified gathering process
#     # final_data = gather_threads(MOCK_DASH, MOCK_UPDATES)
#     # print(json.dumps(final_data, indent=4))
