from datetime import datetime as dt
from queue import Empty

# local imports
from src.scrapers import scrape_jnemulta


def gather(dash, queue_update_data, local_response, total_original, lock):

    CARD = 10

    # log first action
    dash.log(
        card=CARD,
        title=f"JNE Multa [{total_original}]",
        status=1,
        progress=0,
        text="Inicializando",
        lastUpdate="Actualizado:",
    )

    # iterate on every placa and write to database
    while not queue_update_data.empty():

        # grab next record from update queue unless empty
        try:
            id_member, doc_num = queue_update_data.get_nowait()
        except Empty:
            break

        retry_attempts = 0
        while retry_attempts < 3:
            try:
                # log action
                dash.log(card=CARD, text=f"Procesando: {doc_num}")

                # send request to scraper
                jne_response = scrape_jnemulta.browser(doc_num)

                # update memberLastUpdate table with last update information
                _now = dt.now().strftime("%Y-%m-%d")

                # add foreign key and current date to scraper response
                with lock:
                    local_response.append(
                        {
                            "IdMember_FK": id_member,
                            "Existe": jne_response[0] if jne_response else "",
                            "LastUpdate": _now,
                        }
                    )

                # update dashboard with progress, last update timestamp and details
                dash.log(
                    card=CARD,
                    progress=int(
                        ((total_original - queue_update_data.qsize()) / total_original)
                        * 100
                    ),
                    lastUpdate=dt.now(),
                )
                dash.log(
                    action=f"[ JNE MULTAS ] {'|'.join([str(i) for i in local_response[-1].values()])}"
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
        title="JNE Multas",
        progress=100,
        status=3,
        text="Inactivo",
        lastUpdate=dt.now(),
    )
