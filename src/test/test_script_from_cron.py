from src.test import prueba_scrapers, prueba_un_scraper_no_headless
from src.comms import generar_mensajes
from src.updates import datos_actualizar

from pprint import pprint


def main(db):
    # TEST: todo el proceso de mensajes con alertas y boletines
    # do_mensajes.main(db, "alertas")
    # do_mensajes.main(db, "boletines")
    # return

    # TEST: generar boletin fijo
    # from src.test import crear_boletin
    # crear_boletin.main(db, idmember="25", correo="gabfre@gmail.com")
    # return

    # TEST: prueba scrapers
    # prueba_scrapers.main()
    # return

    # TEST: ocr de sunarp
    # from src.test import ocrspace
    # ocrspace.main(self)
    # return

    # prueba_un_scraper_no_headless.main(db)
    # return

    # generar_mensajes.boletines(db)

    a = datos_actualizar.get_datos_nunca_actualizados(db)
    pprint(a)
