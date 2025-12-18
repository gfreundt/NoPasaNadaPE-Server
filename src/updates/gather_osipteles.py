from datetime import datetime as dt
from queue import Empty

# local imports
from src.scrapers import scrape_osiptel


def gather(dash, queue_update_data, local_response, total_original, lock):

    CARD = 11

    # log first action
    dash.log(
        card=CARD,
        title=f"Osiptel [{total_original}]",
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
                osiptel_response = scrape_osiptel.browser(doc_num)

                if not osiptel_response:
                    with lock:
                        local_response.append(
                            {
                                "Empty": True,
                                "IdMember_FK": id_member,
                            }
                        )

                else:

                    # update memberLastUpdate table with last update information
                    _now = dt.now().strftime("%Y-%m-%d")

                    for osip in osiptel_response:
                        with lock:
                            local_response.append(
                                {
                                    "IdMember_FK": id_member,
                                    "TipoLinea": osip[0],
                                    "NumeroLinea": osip[1],
                                    "Operador": osip[2],
                                    "LastUpdate": _now,
                                }
                            )

                # update dashboard with progress, last update timestamp and details of scraped data
                dash.log(
                    card=CARD,
                    progress=int(
                        ((total_original - queue_update_data.qsize()) / total_original)
                        * 100
                    ),
                    lastUpdate=dt.now(),
                )
                dash.log(
                    action=f"[ OSIPTELES ] {'|'.join([str(i) for i in local_response[-1].values()])}"
                )

                # next record
                break

            except KeyboardInterrupt:
                quit()

            # except Exception:
            #     retry_attempts += 1
            #     dash.log(
            #         card=CARD,
            #         text=f"|ADVERTENCIA| Reintentando [{retry_attempts}/3]: {doc_num}",
            #     )

    # log last action
    dash.log(
        card=CARD,
        title="OSIPTEL",
        progress=100,
        status=3,
        text="Inactivo",
        lastUpdate=dt.now(),
    )
