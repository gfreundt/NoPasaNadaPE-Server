from datetime import datetime as dt
from queue import Empty

# local imports
from src.utils.utils import date_to_db_format
from src.scrapers import scrape_sunat


def gather(dash, queue_update_data, local_response, total_original, lock):

    CARD = 8

    # log first action
    dash.log(
        card=CARD,
        title=f"Sunat [{total_original}]",
        status=1,
        progress=0,
        text="Inicializando",
        lastUpdate="Actualizado:",
    )

    # iterate on every placa and write to database
    while not queue_update_data.empty():

        # grab next record from update queue unless empty
        try:
            id_member, doc_tipo, doc_num = queue_update_data.get_nowait()
        except Empty:
            break

        retry_attempts = 0
        while retry_attempts < 3:
            try:
                # log action
                dash.log(card=CARD, text=f"Procesando: {doc_num}")

                # send request to scraper
                sunat_response = scrape_sunat.browser(doc_tipo, doc_num)

                # update memberLastUpdate table with last update information
                _now = dt.now().strftime("%Y-%m-%d")

                # update dashboard with progress and last update timestamp
                dash.log(
                    card=CARD,
                    progress=int(
                        ((total_original - queue_update_data.qsize()) / total_original)
                        * 100
                    ),
                    lastUpdate=dt.now(),
                )

                # response ok, no information available
                if sunat_response == -1:
                    dash.log(
                        card=CARD,
                        status=2,
                        text="Error Scraper",
                        lastUpdate=dt.now(),
                    )
                    break

                if not sunat_response:
                    with lock:
                        local_response.append({"Empty": True, "IdMember_FK": id_member})
                        break

                # response ok, information available

                # adjust date to match db format (YYYY-MM-DD)
                _n = date_to_db_format(data=sunat_response)

                # add foreign key and current date to scraper response
                with lock:
                    local_response.append(
                        {
                            "IdMember_FK": id_member,
                            "NumeroRUC": _n[0],
                            "TipoContribuyente": _n[1],
                            "TipoDocumento": _n[2],
                            "NombreComercial": _n[3],
                            "FechaInscripcion": _n[4],
                            "Estado": _n[5],
                            "Condicion": _n[6],
                            "DomicioFiscal": _n[7],
                            "FechaInicioActividades": _n[8],
                            "LastUpdate": _now,
                        }
                    )

                dash.log(
                    action=f"[ SUNATS ] {'|'.join([str(i) for i in local_response[-1]])}"
                )

                # skip to next record
                break

            except KeyboardInterrupt:
                quit()

            except Exception:
                retry_attempts += 1
                dash.log(
                    card=CARD,
                    text=f"|ADVERTENCIA| Reintentando [{retry_attempts}/3]: {doc_num}",
                )

    # log last action
    dash.log(
        card=CARD,
        title="Sunat",
        progress=100,
        status=3,
        text="Inactivo",
        lastUpdate=dt.now(),
    )
