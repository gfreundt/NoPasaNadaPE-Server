from datetime import datetime as dt

# local imports
from src.scrapers import scrape_recvehic
from src.utils.webdriver import ChromeUtils


def gather(dnis):
    chromedriver = ChromeUtils()
    webdriver = chromedriver.proxy_driver(residential=False)

    for id_member, _, doc_num in dnis:
        try:
            scraper_response = scrape_recvehic.browser_wrapper(
                doc_num=doc_num, webdriver=webdriver
            )

            # si respuesta es texto, hubo un error -- regresar
            if isinstance(scraper_response, str) and len(scraper_response) < 100:
                print(f"RecVehic ({doc_num}): Error: {scraper_response}")
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

            # contruir respuesta
            respuesta = {
                "IdMember_FK": id_member,
                "ImageBytes": scraper_response,
                "LastUpdate": dt.now().strftime("%Y-%m-%d"),
            }
            print("image downloaded successfully")

        except KeyboardInterrupt:
            quit()

        except Exception as e:
            print(f"RecVehic ({doc_num}): Exception: {str(e)}")
            break

    webdriver.quit()
