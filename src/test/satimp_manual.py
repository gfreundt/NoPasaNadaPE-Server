from datetime import datetime as dt

# local imports
from src.scrapers import scrape_satimp
from src.utils.webdriver import ChromeUtils


def gather(docs):
    chromedriver = ChromeUtils()
    webdriver = chromedriver.proxy_driver(residential=False)

    # se tiene un registro, intentar extraer la informacion
    for id_member, _, doc_num in docs:
        try:
            scraper_response = scrape_satimp.browser_wrapper(
                doc_tipo="DNI", doc_num=doc_num, webdriver=webdriver
            )

            if isinstance(scraper_response, str):
                print("Error SATIMPS:", scraper_response)
                continue

            # respuesta es en blanco
            if not scraper_response:
                print(
                    {
                        "Empty": True,
                        "IdMember_FK": id_member,
                    }
                )
                continue

            _now = dt.now().strftime("%Y-%m-%d")

            # contruir respuesta
            for _n in scraper_response:
                print(
                    {
                        "IdMember_FK": id_member,
                        "Codigo": _n["codigo"],
                        "LastUpdate": _now,
                    }
                )
                if _n["deudas"]:
                    for deuda in _n["deudas"]:
                        print(
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
                    print(
                        {
                            "Empty": True,
                            "Codigo": _n["codigo"],
                        }
                    )

        except KeyboardInterrupt:
            quit()

        except Exception as e:
            print(f"SATIMPS ({doc_num}): Crash: {str(e)}")
            break


if __name__ == "__main__":
    d = [(32, "71237579")]
    gather(d)
